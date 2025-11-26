from flask import Blueprint, jsonify

bp = Blueprint('errors', __name__)

@bp.app_errorhandler(404)
def not_found(error):
    return jsonify({"error": "not found"}), 404

@bp.app_errorhandler(400)
def bad_request(error):
    return jsonify({"error": "bad request"}), 400

@bp.app_errorhandler(500)
def server_error(error):
    return jsonify({"error": "internal server error"}), 500
