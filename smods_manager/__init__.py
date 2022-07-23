from flask import Flask
from .api import api_bp
from .api.resources import ma
from flask_cors import CORS


def create_app():
    # create the app
    app = Flask(__name__)

    # enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # init flask-marshmello global object
    ma.init_app(app)

    # register Blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
