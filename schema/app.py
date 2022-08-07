from marshmallow import fields
from marshmallow_union import Union

from schema import ma
from schema.mods import ModRevisionSchema


class ModStatusSchema(ma.Schema):
    class PlaylistInfoSchema(ma.Schema):
        id = fields.String()
        name = fields.String()

    # timestamp = fields.DateTime()
    installed = fields.Nested(ModRevisionSchema(), dump_default=False)
    installing = fields.Boolean()
    downloaded = fields.List(fields.Nested(ModRevisionSchema()))
    starred = fields.Boolean()
    playlists = fields.List(fields.Nested(PlaylistInfoSchema()))
    operation = fields.Dict()

