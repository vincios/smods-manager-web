from flask import Blueprint
from .resources import ModBaseResource, FullModResource, DependencyTreeResource, DownloadUrlResource, SearchResource
from flask_restful import Api

api_bp = Blueprint("api", __name__)
api = Api(api_bp)

api.add_resource(ModBaseResource, "/mod/base/<sid>")
api.add_resource(FullModResource, "/mod/full/<sid>")
api.add_resource(DependencyTreeResource, "/mod/dependencies", "/mod/dependencies/<sid>")
api.add_resource(DownloadUrlResource, "/mod/downlink/<sid>")
api.add_resource(SearchResource, "/search")
