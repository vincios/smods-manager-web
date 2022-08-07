import threading

from flask import request
from flask_restful import Resource

from schema.app import ModStatusSchema
from tasks import uninstall_mod, install_mod
from tasks.mod_operation_utils import create_status_object


class ModStatusResource(Resource):
    def get(self, sid):
        so = create_status_object(sid)
        dumped = ModStatusSchema().dump(so)
        return dumped


class InstallModTask(Resource):
    def post(self):
        data = request.json
        if "mod_id" not in data.keys():
            return {"error": "missing mod_id parameter"}, 400
        if "revision_id" not in data.keys():
            return {"error": "missing revision_id parameter"}, 400

        thread = threading.Thread(target=install_mod, args=(data['mod_id'], data['revision_id'], True,))
        thread.start()

        return {"message": "Accepted"}, 202


class UninstallModTask(Resource):
    def post(self):
        data = request.json
        if "mod_id" not in data.keys():
            return {"error": "missing mod_id parameter"}, 400

        thread = threading.Thread(target=uninstall_mod, args=(data['mod_id'],))
        thread.start()

        return {"message": "Accepted"}, 202
