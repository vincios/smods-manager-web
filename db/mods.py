from sqlalchemy.orm import Session

from smodslib.model import ModBase, ModRevision

from db import engine
from db.model import Mod, ModRevision as DbModRevision


def create_mod_if_not_exists(session, mod: ModBase):
    """
    Warning: THIS FUNCTION DOESN'T ADD TO THE SESSION NOR COMMIT TO THE DATABASE, IT ONLY RETRIEVES FROM DATABASE
    OR CREATE THE MODEL OBJECT!
    """
    new = False
    db_mod = session.query(Mod).filter_by(id=mod.id).first()
    if not db_mod:
        new = True
        db_mod = Mod(mod.id, mod.name)

    return db_mod, new


def create_revision_if_not_exists(session, revision: ModRevision, mod: Mod):
    db_revision = None
    new = False

    for rev in mod.revisions:
        if rev.id == revision.id:
            db_revision = rev
            break

    if not db_revision:
        db_revision = session.query(DbModRevision).filter_by(id=revision.id).first()  # check if created but not added
        if not db_revision:
            db_revision = DbModRevision(revision.id, revision.name, revision.date, revision.download_url,
                                        revision.filename)
            new = True

    return db_revision, new


def get_installed_mods() -> list[Mod]:
    with Session(engine) as sess:
        return sess.query(Mod).filter(Mod.installed_revision_association.has()).all()


def get_installed_revision(mod_id) -> ModRevision:
    with Session(engine) as sess:
        return sess.query(Mod).filter_by(id=mod_id).first().installed_revision_association.revision
