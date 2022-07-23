from flask_restful import Resource
from flask import request

from smodslib import base_mod, full_mod, generate_dependency_tree, generate_download_url_from_id, search
from smodslib.model import CatalogueParameters, SortByFilter, TimePeriodFilter

from flask_marshmallow import Marshmallow
from marshmallow import fields
from marshmallow_union import Union

ma = Marshmallow()


class ModRevisionSchema(ma.Schema):
    name = fields.String()
    date = fields.DateTime()
    download_url = fields.String()


class ModBaseSchema(ma.Schema):
    name = fields.String()
    id = fields.String()
    steam_id = fields.String()
    authors = Union(fields=[fields.String(), fields.List(fields.String())])
    published_date = fields.DateTime()
    size = fields.String()
    has_dependencies = fields.Boolean()
    latest_revision = fields.Nested(ModRevisionSchema)
    steam_url = fields.String()
    url = fields.String()


class FullModSchema(ModBaseSchema):
    description = fields.String()
    plain_description = fields.String()
    updated_date = fields.DateTime()
    dlc_requirements = fields.List(fields.String())
    mod_requirements = fields.List(fields.Nested(ModBaseSchema))
    revisions = fields.List(fields.Nested(ModRevisionSchema))
    tags = fields.List(fields.String())
    category = fields.String()
    image_url = fields.String()
    rating = fields.Integer()


class ModDependencySchema(ModBaseSchema):
    required_by = fields.List(fields.Nested(ModBaseSchema))


class ModCatalogueItemSchema(ModBaseSchema):
    category = fields.String()
    image_url = fields.String()
    rating = fields.Integer()


class ModBaseResource(Resource):
    def get(self, sid):
        return ModBaseSchema().dump(base_mod(sid))


class FullModResource(Resource):
    def get(self, sid):
        return FullModSchema().dump(full_mod(sid))


class DependencyTreeResource(Resource):
    def get(self, sid=None):
        if not sid and "mods" in request.args.keys():
            mods = request.args.getlist("mods")
        elif sid:
            mods = [sid]
        else:
            return {"error": "Missing mod id or ids list"}, 400

        return ModDependencySchema(many=True).dump(generate_dependency_tree(mods, recursive=True))


class DownloadUrlResource(Resource):
    def get(self, sid):
        return {"url": generate_download_url_from_id(sid)}


class SearchResource(Resource):
    def get(self):
        query = request.args.get("q")
        page = request.args.get("page", 0)
        sort = request.args.get("sort")
        period = request.args.get("period")

        filters = None

        if not query:
            return {"error": "Missing q parameter"}, 400

        if sort or period:
            sort = SortByFilter(sort) if sort else None
            period = TimePeriodFilter(period) if period else None
            filters = CatalogueParameters(sort=sort, period=period)

        return ModCatalogueItemSchema(many=True).dump(search(query, page, filters))
