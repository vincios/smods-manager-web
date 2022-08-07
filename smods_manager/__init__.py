from flask import Flask
from .api import api_bp
from flask_cors import CORS

from schema import ma as app_ma
from db import flask_db, db_path


def create_app():
    # create the app
    app = Flask(__name__)

    # enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # init flask-marshmello global object
    # mods_ma.init_app(app)
    app_ma.init_app(app)

    # init sqlalchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    flask_db.init_app(app)

    # register Blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    print(app.url_map)
    return app
