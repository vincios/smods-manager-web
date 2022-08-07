import datetime
from typing import Any, TypedDict, List

from smodslib.model import ModRevision


class WebsocketMessage(TypedDict):
    type: str  # message type: status, ...
    channel: str  # message identifier to distinguish between messages
    payload: Any  # content of the message


class ModStatus(object):
    timestamp: datetime.datetime
    installed: ModRevision | bool
    downloaded: List[ModRevision] | bool
    starred: bool
    playlists: List[dict]
    installing: bool
    operation: dict

    def __init__(self, installed: ModRevision | bool = False,
                 downloaded: List[ModRevision] | bool = False, starred: bool = False, playlists: List[dict] = None,
                 installing: bool = False, operation: dict = None):

        if playlists is None:
            playlists = []

        self.installed = installed
        self.downloaded = downloaded
        self.starred = starred
        self.playlists = playlists
        self.installing = installing
        self.operation = operation
