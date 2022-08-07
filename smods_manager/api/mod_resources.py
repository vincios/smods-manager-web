from flask_restful import Resource
from flask import request

from smodslib import base_mod, full_mod, generate_dependency_tree, generate_download_url_from_id, search
from smodslib.smods import get_mod_revisions

from smodslib.model import CatalogueParameters, SortByFilter, TimePeriodFilter

from schema.mods import ModDependencySchema, ModBaseSchema, FullModSchema, ModRevisionSchema, ModCatalogueItemSchema


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


class OtherRevisionsResource(Resource):
    def get(self, sid):
        _, other_revisions = get_mod_revisions(sid)
        if not other_revisions:
            other_revisions = []
        return ModRevisionSchema(many=True).dump(other_revisions)


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
