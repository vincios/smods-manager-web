from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy_serializer import SerializerMixin

from db import Base


class InstalledRevisions(Base, SerializerMixin):
    __tablename__ = "InstalledRevisions"
    mod_id = Column(ForeignKey("Mod.id"), primary_key=True)
    revision_id = Column(ForeignKey("ModRevision.id"), primary_key=True)
    status = Column(String(20))
    path = Column(String(255), nullable=True)
    revision = relationship('ModRevision')

    def __init__(self, status, path=None):
        self.status = status
        self.path = path


class DownloadedRevisions(Base, SerializerMixin):
    __tablename__ = "DownloadedRevisions"
    mod_id = Column(ForeignKey("Mod.id"), primary_key=True)
    revision_id = Column(ForeignKey("ModRevision.id"), primary_key=True)
    path = Column(String(255))
    revision = relationship('ModRevision')

    def __init__(self, path):
        self.path = path


class ModsPlaylists(Base, SerializerMixin):
    __tablename__ = "ModsPlaylists"
    mod_id = Column(ForeignKey("Mod.id"), primary_key=True)
    playlist_id = Column(ForeignKey("Playlist.id"), primary_key=True)
    date_added = Column(DateTime)

    mod = relationship("Mod", back_populates="playlists_association")
    playlist = relationship('Playlist', back_populates="mods_association")


class ModDependencies(Base, SerializerMixin):
    __tablename__ = "ModDependencies"
    mod_id = Column(ForeignKey("Mod.id"), primary_key=True)
    dependency_id = Column(ForeignKey("Mod.id"), primary_key=True)


class ModRevision(Base, SerializerMixin):
    __tablename__ = "ModRevision"
    serialize_rules = ('-mod',)

    id = Column(String(10), primary_key=True)
    name = Column(String(50), nullable=False)
    date = Column(DateTime, nullable=False)
    download_url = Column(String(200), nullable=False)
    filename = Column(String(100), nullable=False)
    mod_id = Column(String(20), ForeignKey('Mod.id'), nullable=False)

    def __init__(self, id, name, date, download_url, filename):
        self.id = id
        self.name = name
        self.date = date
        self.download_url = download_url
        self.filename = filename


class Mod(Base, SerializerMixin):
    __tablename__ = "Mod"
    serialize_rules = ('-dependants.dependencies', '-dependencies.dependencies',
                       '-dependants.dependants', '-dependencies.dependants',
                       '-playlists_association.mod.playlists_association', '-playlists_association.playlist.mods_association', )

    id = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=True)
    revisions = relationship("ModRevision", backref="mod")
    installed_revision_association = relationship("InstalledRevisions", uselist=False)
    downloaded_revisions_association = relationship("DownloadedRevisions")
    playlists_association = relationship("ModsPlaylists", back_populates='mod')
    # dependencies = relationship("Mod", secondary="ModDependencies", back_populates="dependants")
    # dependencies relationship above is commented because dependants relationship below automatically creates it
    #   with the backref argument
    dependencies = relationship("Mod", secondary="ModDependencies", backref="dependants",
                                primaryjoin=id == ModDependencies.mod_id, secondaryjoin=id == ModDependencies.dependency_id)
    # dependencies = []

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def add_downloaded(self, revision: ModRevision, path: str):
        already_added = None
        for dr in self.downloaded_revisions_association:
            if dr.revision.id == revision.id:
                already_added = dr.revision
                break

        if already_added:
            already_added.path = path
        else:
            dr = DownloadedRevisions(path=path)
            dr.revision = revision
            self.downloaded_revisions_association.append(dr)

    def set_installed(self, revision: ModRevision, status: str = None, path: str = None):
        if self.installed_revision_association and self.installed_revision_association.revision.id == revision.id:
            self.installed_revision_association.revision.status = status
            self.installed_revision_association.revision.path = path
        elif self.installed_revision_association:
            raise ValueError(f"Another revision with id {self.installed_revision_association.revision.id} installed")
        else:
            db_installed_revision = InstalledRevisions(status=status, path=path)
            db_installed_revision.revision = revision
            self.installed_revision_association = db_installed_revision

    def add_dependency(self, dependency):
        self.dependencies.append(dependency)


class Playlist(Base, SerializerMixin):
    __tablename__ = "Playlist"
    serialize_rules = ('-mods_association',)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    mods_association = relationship("ModsPlaylists", back_populates='playlist')

    def __init__(self, name):
        self.name = name


class Configuration(Base, SerializerMixin):
    __tablename__ = "Configuration"
    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=True)

    def __init__(self, key, value=None):
        self.key = key
        self.value = value
