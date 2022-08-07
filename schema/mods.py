from marshmallow import fields
from marshmallow_union import Union

from schema import ma


class ModRevisionSchema(ma.Schema):
    id = fields.String()
    name = fields.String()
    date = fields.DateTime()
    download_url = fields.String()
    filename = fields.String()


class ModBaseSchema(ma.Schema):
    name = fields.String()
    id = fields.String()
    steam_id = fields.String()
    authors = Union(fields=[fields.String(), fields.List(fields.String())])
    published_date = fields.DateTime()
    size = fields.String()
    has_dependencies = fields.Boolean()
    latest_revision = fields.Nested(ModRevisionSchema())
    category = fields.String()
    steam_url = fields.String()
    url = fields.String()


class FullModSchema(ModBaseSchema):
    description = fields.String()
    plain_description = fields.String()
    updated_date = fields.DateTime()
    dlc_requirements = fields.List(fields.String())
    mod_requirements = fields.List(fields.Nested(ModBaseSchema()))
    other_revisions = fields.List(fields.Nested(ModRevisionSchema()))
    tags = fields.List(fields.String())
    category = fields.String()
    image_url = fields.String()
    rating = fields.Integer()


class ModDependencySchema(ModBaseSchema):
    required_by = fields.List(fields.Nested(ModBaseSchema()))


class ModCatalogueItemSchema(ModBaseSchema):
    category = fields.String()
    image_url = fields.String()
    rating = fields.Integer()
