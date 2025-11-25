from flask import Blueprint, jsonify

bp = Blueprint("errors", __name__)

@bp.app_errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@bp.app_errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400
