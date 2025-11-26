import os
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize SQLAlchemy
    from .models import db
    db.init_app(app)

    # Register CLI commands
    from . import commands
    commands.init_app(app)

    # Register blueprints
    from . import users
    app.register_blueprint(users.bp)

    from . import property
    app.register_blueprint(property.bp)

    from .errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    @app.route('/', methods=['GET'])
    def index():
        return jsonify({"service": "property-management", "status": "ok"}), 200

    return app