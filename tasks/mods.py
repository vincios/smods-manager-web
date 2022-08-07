import os
import shutil
from functools import partial
from tempfile import mkdtemp
from typing import Union

import websocket
from smodslib import generate_dependency_tree, generate_download_url, base_mod
from smodslib.download import download_revision
from smodslib.model import ModBase
from smodslib.smods import get_mod_revisions
from sqlalchemy.orm import Session

from smods_manager.app import download_folder, get_asset_target_folder
from db import engine, SSession
from db.app import get_configuration, CONFIGURATION_KEYS
from db.model import ModRevision, DownloadedRevisions, Mod
from db.mods import create_mod_if_not_exists, create_revision_if_not_exists, get_installed_mods
from tasks.mod_operation_utils import create_status_object, op_state
from utils.utils import wait_for_file, unzip, copydir
from smods_websocket.client import send_status
from utils.logger import get_logger

logger = get_logger(__name__)


def install_mod(mod_or_id: Union[str, ModBase], revision_id: str, install_deps=False,
                ws: websocket.WebSocket = None, child=False):  # if we already have a websocket, why don't reuse it?
    mod_id = mod_or_id.id if isinstance(mod_or_id, ModBase) else mod_or_id
    to_install_mod = mod_or_id if isinstance(mod_or_id, ModBase) else None

    logger.info(f"Installing revision {revision_id} of mod {mod_id}")
    db = SSession()

    tmpdir = mkdtemp(prefix="smods_manager-")
    status_object = create_status_object(mod_id)
    status_object.installing = True

    install_op_object = partial(op_state, "install")
    rollback_fn = None  # checks when we can do rollback

    if not ws:
        logger.info("Connecting to websocket")
        ws = websocket.create_connection("ws://localhost:5001")

    ws_send_status = partial(send_status, ws, mod_id)

    if not get_configuration(CONFIGURATION_KEYS.CS_INSTALL_DIR) or not get_configuration(
            CONFIGURATION_KEYS.CS_DATA_DIR):
        logger.warn("CS folders paths not into database. Maybe you forgot to add them to the configurations?")
        status_object.operation = install_op_object("error", mod=to_install_mod, data={
            "code": "no_path_configuration",
            "message": f"CS folders location not found. Please check your configuration"})
        ws_send_status(status_object)
        return

    # STEP 1: get mod info
    logger.info("STEP 1: get mod info")
    status_object.operation = install_op_object("get_mod_info")
    logger.debug(status_object)
    ws_send_status(status_object)

    if not to_install_mod:
        logger.info("Retrieving mod object from smods.ru")
        to_install_mod = base_mod(mod_id)

    to_install_revision = None

    if not revision_id or revision_id == to_install_mod.latest_revision.id:
        to_install_revision = to_install_mod.latest_revision
    else:
        latest_revision, other_revision = get_mod_revisions(mod_id)
        revisions = other_revision + [latest_revision]
        for rev in revisions:
            if rev.id == revision_id:
                to_install_revision = rev
                break

    if not to_install_revision:
        logger.warn(f"Revision {revision_id} doesn't exists")
        status_object.operation = install_op_object("error", mod=to_install_mod, data={
            "code": "revision_not_found",
            "message": f"Revision not found: {revision_id}"})
        ws_send_status(status_object)
        return

    logger.info(f"Mod name: {to_install_mod.name} - Revision: {to_install_revision.name}")
    try:
        db_mod, is_new = create_mod_if_not_exists(db, to_install_mod)
        if is_new:
            logger.info("New Mod object added to the database")
            db.add(db_mod)

        if db_mod.installed_revision_association:
            logger.warn(f"Another revision ({db_mod.installed_revision_association.revision.name}) is already installed")
            status_object.operation = install_op_object("error", mod=to_install_mod, data={
                "code": "mod_already_installed",
                "message": f"Another revision already installed: {db_mod.installed_revision_association.revision.name}",
                "installed_revision": db_mod.installed_revision_association.revision.to_dict()
            })
            status_object.installed = db_mod.installed_revision_association.revision
            ws_send_status(status_object)
            return

        db_revision, is_new = create_revision_if_not_exists(db, to_install_revision, db_mod)

        if is_new:
            logger.info("New Revision object added to the database")
            db.add(db_revision)
            with db.no_autoflush:
                # we have to disable autoflush for this statement, because if db_mod is new, until the commit db_mod
                # has Null id, so the autoflush tries to insert db_revision into the database with
                # db_revision.mod_id=None, which violates the NOT NULL constraint
                db_mod.revisions.append(db_revision)

        db_mod.set_installed(db_revision, status="installing")
        db_installed_revision = db_mod.installed_revision_association

        # save this information for future accesses
        logger.info("First commit to the database")
        db.commit()

        def rollback():
            logger.info("Rollback: removing the InstalledRevision object from the database")
            db.delete(db_installed_revision)
            db.commit()

        rollback_fn = rollback

        # recreate the status object with new saved information
        status_object = create_status_object(mod_id)

        # STEP 2: get dependencies
        logger.info("STEP 2: install dependencies")
        if not install_deps:
            logger.info("Argument install_deps is False: skipping step 2")
        elif not to_install_mod.has_dependencies:
            logger.info("This mod doesn't have dependencies. Slipping step 2")

        if install_deps and to_install_mod.has_dependencies:
            status_object.operation = install_op_object("get_dependencies", mod=to_install_mod,
                                                        revision=to_install_revision)
            ws_send_status(status_object)

            logger.info("Generating dependencies tree...")
            deps = generate_dependency_tree(to_install_mod.id)
            logger.info(f"{len(deps)} dependencies found")
            logger.info(f"Installation of {to_install_mod.name} will continue after all the dependencies")

            to_install_list: list[tuple[ModBase, ModRevision]] = [(m, m.latest_revision) for m in deps]
            installed_mods = [im.id for im in get_installed_mods() if im.id != mod_id]

            for m, r in to_install_list:
                # we exclude the to_install_mod from this check,
                # because here we are interested to the dependencies only
                # TODO: not necessary anymore, since now to_install_list has only dependencies?
                if m.id != to_install_mod.id and m.id in installed_mods:
                    continue  # TODO: check for updates?

                logger.info(f"Installing dependency: {m.name}...")
                status_object.operation = install_op_object("installing_dependency", mod=m, revision=r)
                ws_send_status(status_object)

                # RECURSION!
                # install_deps is False because this is an half recursion: all dependencies in the dependency tree
                # have already been recursively added to the "deps" variable -> TODO: make a full recursion?
                install_mod(m, r.id, install_deps=False, child=True)

                # we add m to the dependencies list of db_mod because here we are sure that install_mod
                # have created (if necessary) the database entry for m
                db_m = db.query(Mod).filter_by(id=m.id).first()
                db_mod.add_dependency(db_m)

        # STEP 3: Download revision -> This steps and next ones below will start only when the recursion above
        # have installed all the deps
        logger.info("STEP 3: downloading Revision")
        status_object.operation = install_op_object("get_download_url", mod=to_install_mod,
                                                    revision=to_install_revision)
        ws_send_status(status_object)

        # we check if the revision is already downloaded (already saved into database), so we don't have to download
        # it again
        db_downloaded_revision = db.query(DownloadedRevisions) \
            .filter(DownloadedRevisions.mod_id == to_install_mod.id,
                    DownloadedRevisions.revision_id == to_install_revision.id).first()

        if db_downloaded_revision and os.path.exists(db_downloaded_revision.path):
            logger.info("Revision already downloaded: skipping step 3")
            # file already downloaded
            zip_file_path = db_downloaded_revision.path
        else:
            if db_downloaded_revision and not os.path.exists(db_downloaded_revision.path):
                logger.warn("The Revision seems to be already downloaded, but the file doesn't exists into the "
                            "filesystem. Downloading it again...")
                # file removed manually, or wrong path -> delete from database
                db_mod.downloaded_revisions_association.remove(db_downloaded_revision)
                db.delete(db_downloaded_revision)

            logger.info("Generating download url...")
            url = generate_download_url(to_install_revision)
            if url == 403:
                logger.info("Server responded with a 403 Unauthorized error. Waiting that the user manually downloads "
                            "the zip file...")
                status_object.operation = install_op_object("wait_for_file", mod=to_install_mod,
                                                            revision=to_install_revision,
                                                            data={"timeout": 500, "download_folder": download_folder})
                ws_send_status(status_object)
                try:
                    zip_file_path = wait_for_file(os.path.join(download_folder, to_install_revision.filename), timeout=500)
                except TimeoutError:
                    logger.warn("Waiting timeout: the user doesn't have downloaded the file")
                    status_object.operation = install_op_object("error", mod=to_install_mod,
                                                                revision=to_install_revision,
                                                                data={"code": "timeout",
                                                                      "message": "File download timeout"})
                    ws_send_status(status_object)
                    return
            elif isinstance(url, int):
                # generic error:
                logger.error(f"The server responded with a {url} error")
                status_object.operation = install_op_object("error", mod=to_install_mod,
                                                            revision=to_install_revision,
                                                            data={"code": "http_error",
                                                                  "message": f"Http error during get_download_url: {url}"})
                ws_send_status(status_object)
                return
            else:
                logger.info(f"Download url: {url}")

                def progress_callback(downloaded, total):
                    status_object.operation = install_op_object("downloading", mod=to_install_mod,
                                                                revision=to_install_revision,
                                                                data={"downloaded_bytes": downloaded,
                                                                      "total_bytes": total})
                    ws_send_status(status_object)

                def error_callback(http_code, http_message):
                    logger.error(f"Download stopped with error {http_code}: {http_message}")
                    status_object.operation = install_op_object("error", mod=to_install_mod,
                                                                revision=to_install_revision,
                                                                data={"code": "http_error", "message": http_message,
                                                                      "http_code": http_code})
                    ws_send_status(status_object)

                logger.info("Downloading file...")
                res = download_revision(url, download_folder, progress_callback, error_callback)
                if res == 403:
                    logger.info("Server responded with a 403 Unauthorized error. Waiting that the user manually "
                                "downloads the zip file...")
                    status_object.operation = install_op_object("wait_for_file", mod=to_install_mod,
                                                                revision=to_install_revision,
                                                                data={"timeout": 500, "download_folder": download_folder})
                    ws_send_status(status_object)
                    try:
                        zip_file_path = wait_for_file(os.path.join(download_folder, to_install_revision.filename), timeout=500)
                    except TimeoutError:
                        logger.warn("Waiting timeout: the user doesn't have downloaded the file")
                        status_object.operation = install_op_object("error", mod=to_install_mod,
                                                                    revision=to_install_revision,
                                                                    data={"code": "timeout",
                                                                          "message": "File download timeout"})
                        ws_send_status(status_object)
                        return
                elif isinstance(res, int):
                    # generic error:
                    logger.error(f"The server responded with a {url} error")
                    status_object.operation = install_op_object("error", mod=to_install_mod,
                                                                revision=to_install_revision,
                                                                data={"code": "http_error",
                                                                      "message": f"Http error during downloading: {url}"})
                    ws_send_status(status_object)
                    return
                else:
                    # file downloaded successfully
                    logger.info(f"File downloaded successfully to path {res}")
                    zip_file_path = res
                    # save the downloaded revision in database
                    db_mod.add_downloaded(db_revision, zip_file_path)

        # STEP 4: Unzip
        logger.info("STEP 4: unzip")
        if not isinstance(zip_file_path, str) or not os.path.exists(zip_file_path):
            logger.warn(f"No zip file found at path {zip_file_path}")
            status_object.operation = install_op_object("error", mod=to_install_mod, revision=to_install_revision,
                                                        data={"code": "zip_error",
                                                              "message": "Zip file not found"})
            ws_send_status(status_object)
            return

        status_object.operation = install_op_object("unzip", mod=to_install_mod, revision=to_install_revision)
        ws_send_status(status_object)

        unzipped_folder_path = unzip(zip_file_path, tmpdir)
        logger.info(f"File successfully unzipped at path {tmpdir}")

        # STEP 5 Install
        logger.info("STEP 5: install")
        status_object.operation = install_op_object("copying", mod=to_install_mod, revision=to_install_revision)
        ws_send_status(status_object)

        target_folder = get_asset_target_folder(to_install_mod)

        # we get unzipped folder name to save it to the database
        root, dirs, files = next(os.walk(tmpdir))
        unzipped_folder_name = dirs[0]

        def copy_callback(copied, total):
            status_object.operation = install_op_object("copying", mod=to_install_mod, revision=to_install_revision,
                                                        data={"copied_bytes": copied, "total_bytes": total})
            ws_send_status(status_object)

        logger.info(f"Target folder: {target_folder}")
        copydir(tmpdir, target_folder, callback=copy_callback)
        db_installed_revision.path = os.path.join(target_folder, unzipped_folder_name)
        db_installed_revision.status = "installed"
        # DONE!
        logger.info(f"Revision successfully installed at path {db_installed_revision.path}")

        # save all the changes to the database
        db.commit()

        # we recreate the status object one last time with the information just saved into the database
        status_object = create_status_object(mod_id)

        status_object.operation = install_op_object("done", mod=to_install_mod, revision=to_install_revision)
        ws_send_status(status_object)
        logger.info("Install completed")

    # except ConnectionAbortedError:
    #     # don't stop in case of websocket error
    #     logger.warn("WebSocket connection error. Trying to continue without the ws")
    #     pass
    except Exception as e:
        logger.error("An error have occurred", e)
        db.rollback()
        if rollback_fn:
            rollback_fn()

            try:
                status_object.operation = install_op_object("error", mod=to_install_mod, revision=to_install_revision,
                                                            data={"code": "exception", "message": str(e)})
                ws_send_status(status_object)
            except ConnectionAbortedError:
                # don't stop in case of websocket error
                pass
        raise
    finally:
        logger.info("Closing resources and deleting temporary folders...")
        if ws:
            ws.close()
        if not child:
            # TODO: find a better approach to close the scoped session when the recursion ends.
            # For now, we use a parameter "child" that is False only for the first iteration, but if the caller change
            # the value of this parameter, the function broke
            SSession.remove()
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


def uninstall_mod(mod_or_id: Union[str, ModBase]):
    mod_id = mod_or_id.id if isinstance(mod_or_id, ModBase) else mod_or_id
    ws, db = None, None

    status_object = create_status_object(mod_id)
    uninstall_op_object = partial(op_state, "uninstall")
    ws_send_status = None

    logger.info(f"Uninstalling mod {mod_id}")
    try:
        logger.info("Connecting to the database...")
        db = Session(engine)
        print("Connecting to the WebSocket")
        ws = websocket.create_connection("ws://localhost:5001")

        ws_send_status = partial(send_status, ws, mod_id)

        logger.info("Getting mod info")
        status_object.operation = uninstall_op_object("get_mod_info")
        ws_send_status(status_object)
        db_mod = db.query(Mod).filter_by(id=mod_id).first()

        if not db_mod:
            logger.warn(f"Mod with id {mod_id} not found")
            status_object.operation = uninstall_op_object("error", data={
                "code": "mod_not_found",
                "message": f"Mod not found: {mod_id}"
            })
            ws_send_status(status_object)
            return

        if not db_mod.installed_revision_association:
            logger.warn(f"No installed revision for Mod with id {mod_id}")
            status_object.operation = uninstall_op_object("error", data={
                "code": "mod_not_installed",
                "message": f"No installed revision for Mod: {mod_id}"
            })
            ws_send_status(status_object)
            return

        ir = db_mod.installed_revision_association

        # STEP 1: remove folder from the installing path
        logger.info(f"Deleting the install path: {ir.path}")
        status_object.operation = uninstall_op_object("remove_folder")
        ws_send_status(status_object)

        if os.path.exists(ir.path):
            shutil.rmtree(ir.path, ignore_errors=True)

        # STEP 2: removing InstalledRevision entry from the database
        logger.info("Removing InstalledRevision entry from the database...")
        status_object.operation = uninstall_op_object("remove_database_entry")
        ws_send_status(status_object)
        db_mod.installed_revision_association = None
        db.delete(ir)

        db.commit()

        # done

        # we recreate the status object one last time with the information just saved into the database
        status_object = create_status_object(mod_id)
        status_object.operation = uninstall_op_object("done")
        ws_send_status(status_object)
        logger.info("Uninstall completed")
    except ConnectionAbortedError:
        # don't stop in case of websocket error
        logger.warn("WebSocket connection error. Trying to continue without the ws")
        pass
    except Exception as e:
        logger.error("An error have happened", e)
        db.rollback()
        if ws_send_status:
            try:
                status_object.operation = uninstall_op_object("error", data={"code": "exception", "message": str(e)})
                ws_send_status(status_object)
            except ConnectionAbortedError:
                # don't stop in case of websocket error
                pass
        raise
    finally:
        logger.info("Closing resources...")
        if ws:
            ws.close()
        if db:
            db.close()
