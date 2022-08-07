from flask import Blueprint

from .app_resources import ModStatusResource, InstallModTask, UninstallModTask
from .mod_resources import ModBaseResource, FullModResource, DependencyTreeResource, DownloadUrlResource, \
    SearchResource, OtherRevisionsResource
from flask_restful import Api

mods_bp = Blueprint("mod", __name__, url_prefix="/mod")
app_bp = Blueprint("app", __name__, url_prefix="/app")

api_bp = Blueprint("api", __name__)
app_api = Api(app_bp)
mods_api = Api(mods_bp)


mods_api.add_resource(ModBaseResource, "/<sid>/base")
mods_api.add_resource(FullModResource, "/<sid>/full")
mods_api.add_resource(OtherRevisionsResource, '/<sid>/other_revisions')
mods_api.add_resource(DependencyTreeResource, "/dependencies", "/<sid>/dependencies/")  # mods list as query parameter if more than one sid
mods_api.add_resource(DownloadUrlResource, "/downlink/<sid>")
mods_api.add_resource(SearchResource, "/search")

app_api.add_resource(ModStatusResource, "/status/<sid>")
app_api.add_resource(InstallModTask, "/install")  # parameters as POST request body
app_api.add_resource(UninstallModTask, "/uninstall")  # parameter as POST request body


api_bp.register_blueprint(mods_bp)
api_bp.register_blueprint(app_bp)





