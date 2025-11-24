import os

from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE_URL=os.environ.get('DATABASE_URL'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import users 
    app.register_blueprint(users.bp)

    from . import property
    app.register_blueprint(property.bp)

    @app.route('/', methods=['GET'])
    def index():
        return jsonify({"service": "property-management", "status": "ok"}), 200

    return app
