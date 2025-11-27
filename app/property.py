import json
from typing import Any, Dict, List, Tuple

from flask import Blueprint, jsonify, request

from app.db import get_db

bp = Blueprint('property', __name__, url_prefix='/properties')


def get_current_user_id() -> int | None:
    """Dev-only auth: read current user id from X-User-Id header."""
    raw = request.headers.get('X-User-Id')
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _serialize_property(row: Dict[str, Any]) -> Dict[str, Any]:
    rooms_details = row.get('rooms_details')
    parsed_rooms: List[Any]

    if isinstance(rooms_details, str) and rooms_details:
        try:
            parsed_rooms = json.loads(rooms_details)
        except json.JSONDecodeError:
            parsed_rooms = []
    elif isinstance(rooms_details, list):
        parsed_rooms = rooms_details
    else:
        parsed_rooms = []

    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "property_type": row["property_type"],
        "city": row["city"],
        "rooms_count": row["rooms_count"],
        "rooms_details": parsed_rooms,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "owner": {
            "id": row["owner_id"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
        },
    }


def _fetch_property(property_id: int) -> Dict[str, Any] | None:
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT p.*, u.first_name, u.last_name
            FROM properties p
            JOIN users u ON p.owner_id = u.id
            WHERE p.id = %s;
            """,
            (property_id,),
        )
        row = cur.fetchone()
    return row


@bp.get('')
def list_properties():
    """List all properties, optionally filtered by city, with simple pagination."""
    db = get_db()

    # City is required in filter
    city = (request.args.get('city') or '').strip()
    if not city:
        return jsonify({"error": "city query parameter is required"}), 400

    # pagination
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(request.args.get("page_size", 20))
    except (TypeError, ValueError):
        page_size = 20

    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    offset = (page - 1) * page_size

    city = (request.args.get('city') or '').strip()

    base_query = """
        SELECT p.*, u.first_name, u.last_name
        FROM properties p
        JOIN users u ON p.owner_id = u.id
    """
    params: List[Any] = []

    if city:
        base_query += " WHERE LOWER(p.city) = LOWER(%s)"
        params.append(city)

    base_query += " ORDER BY p.created_at DESC LIMIT %s OFFSET %s"
    params.extend([page_size, offset])

    with db.cursor() as cur:
        cur.execute(base_query, tuple(params))
        rows = cur.fetchall()

    return jsonify({
        "properties": [_serialize_property(row) for row in rows],
        "page": page,
        "page_size": page_size,
    }), 200


@bp.get('/<int:property_id>')
def retrieve_property(property_id: int):
    """Get a single property by id."""
    property_row = _fetch_property(property_id)
    if property_row is None:
        return jsonify({"error": "property not found"}), 404
    return jsonify({"property": _serialize_property(property_row)}), 200


def _extract_property_payload(
    payload: Dict[str, Any], *, partial: bool = False
) -> Tuple[Dict[str, Any] | None, str | None]:
    """Validate and normalize property payload."""
    fields: Dict[str, Any] = {}
    required_fields = ('name', 'description', 'property_type', 'city')

    for field in required_fields:
        if field in payload:
            value = payload.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return None, f"{field} cannot be empty"
            fields[field] = value.strip() if isinstance(value, str) else value
        elif not partial:
            return None, f"{field} is required"

    rooms_details_provided = 'rooms_details' in payload
    rooms_details_value = payload.get('rooms_details')
    if rooms_details_provided:
        if rooms_details_value in (None, ''):
            rooms_details_value = []
        if not isinstance(rooms_details_value, list):
            return None, "rooms_details must be a list"
        fields['rooms_details'] = json.dumps(rooms_details_value)
    elif not partial:
        rooms_details_value = []
        fields['rooms_details'] = json.dumps(rooms_details_value)

    rooms_count_provided = 'rooms_count' in payload
    rooms_count_value = payload.get('rooms_count')

    if not rooms_count_provided and rooms_details_provided:
        rooms_count_value = len(rooms_details_value or [])
        rooms_count_provided = True

    if rooms_count_provided:
        try:
            rooms_count_int = int(rooms_count_value)
        except (TypeError, ValueError):
            return None, "rooms_count must be an integer"
        fields['rooms_count'] = max(0, rooms_count_int)
    elif not partial:
        fields['rooms_count'] = len(rooms_details_value or [])

    return fields, None


@bp.post('')
def create_property():
    """Create a new property owned by the current user."""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({"error": "X-User-Id header is required"}), 401

    payload = request.get_json(silent=True) or {}
    fields, error = _extract_property_payload(payload)
    if error:
        return jsonify({"error": error}), 400

    db = get_db()

    # Optional: ensure owner exists
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id = %s;", (current_user_id,))
        owner = cur.fetchone()
        if owner is None:
            return jsonify({"error": "owner user not found"}), 400

        cur.execute(
            """
            INSERT INTO properties (
                name, description, property_type, city,
                rooms_count, rooms_details, owner_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                fields['name'],
                fields['description'],
                fields['property_type'],
                fields['city'],
                fields['rooms_count'],
                fields['rooms_details'],
                current_user_id,
            ),
        )
        inserted = cur.fetchone()

    db.commit()
    created_at = _fetch_property(inserted['id'])
    return jsonify({"property": _serialize_property(created_at)}), 201


@bp.route('/<int:property_id>', methods=('PUT', 'PATCH'))
def update_property(property_id: int):
    """Update a property (only owner can edit)."""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({"error": "X-User-Id header is required"}), 401

    property_row = _fetch_property(property_id)
    if property_row is None:
        return jsonify({"error": "property not found"}), 404

    if property_row['owner_id'] != current_user_id:
        return jsonify({"error": "you can only edit your own properties"}), 403

    payload = request.get_json(silent=True) or {}
    fields, error = _extract_property_payload(payload, partial=True)
    if error:
        return jsonify({"error": error}), 400
    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    assignments = ', '.join(f"{column} = %s" for column in fields.keys())
    assignments += ', updated_at = CURRENT_TIMESTAMP'
    values = tuple(list(fields.values()) + [property_id])

    db = get_db()
    with db.cursor() as cur:
        cur.execute(f'UPDATE properties SET {assignments} WHERE id = %s;', values)
    db.commit()

    updated_at = _fetch_property(property_id)
    return jsonify({"property": _serialize_property(updated_at)}), 200


@bp.delete('/<int:property_id>')
def delete_property(property_id: int):
    """Delete a property (only owner can delete)."""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({"error": "X-User-Id header is required"}), 401

    property_row = _fetch_property(property_id)
    if property_row is None:
        return jsonify({"error": "property not found"}), 404

    if property_row['owner_id'] != current_user_id:
        return jsonify({"error": "you can only delete your own properties"}), 403

    db = get_db()
    with db.cursor() as cur:
        cur.execute('DELETE FROM properties WHERE id = %s;', (property_id,))
    db.commit()
    return jsonify({"message": "property deleted"}), 200
