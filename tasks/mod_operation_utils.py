from smodslib.model import ModBase, ModRevision
from sqlalchemy.orm import Session

from db import engine
from db.model import Mod
from schema.mods import ModBaseSchema, ModRevisionSchema
from smods_websocket.model import ModStatus


def create_status_object(mod_id: str) -> ModStatus:
    installed = None
    installing = False
    downloaded = None
    starred = False
    playlists = []

    with Session(engine) as db:
        db_mod = db.query(Mod).filter_by(id=mod_id).first()
        if db_mod:
            # installed / installing
            if db_mod.installed_revision_association:
                installed = db_mod.installed_revision_association.revision
                if db_mod.installed_revision_association.status.lower() == "installing":
                    installing = True

            # downloaded
            if db_mod.downloaded_revisions_association:
                downloaded = []
                for dr in db_mod.downloaded_revisions_association:
                    downloaded.append(dr.revision)

            # starred / playlists
            for pa in db_mod.playlists_association:
                if pa.playlist.id == 0:  # playlist 0 is starred mods
                    starred = True
                else:
                    playlists.append(pa.playlist)

    return ModStatus(installed=installed, downloaded=downloaded, starred=starred, playlists=playlists,
                     installing=installing)


def op_state(operation: str, state: str, mod: ModBase | None = None,
             revision: ModRevision | None = None, data: dict | None = None) -> dict:
    base = {
        "op": operation,
        "state": state,
    }

    if mod:
        base["mod"] = ModBaseSchema().dump(mod)
        # base["mod"] = mod
    if revision:
        base["revision"] = ModRevisionSchema().dump(revision)
        # base["revision"] = revision

    return base if not data else base | data
