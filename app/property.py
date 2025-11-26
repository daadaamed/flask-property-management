import json
from typing import Dict, Any, Tuple

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from .models import db, Property, User

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


def _serialize_property(prop: Property) -> Dict[str, Any]:
    """Serialize a Property object with parsed rooms_details."""
    rooms_details = prop.rooms_details
    parsed_rooms = []
    
    if isinstance(rooms_details, str) and rooms_details:
        try:
            parsed_rooms = json.loads(rooms_details)
        except json.JSONDecodeError:
            parsed_rooms = []
    elif isinstance(rooms_details, list):
        parsed_rooms = rooms_details
    
    return {
        "id": prop.id,
        "name": prop.name,
        "description": prop.description,
        "property_type": prop.property_type,
        "city": prop.city,
        "rooms_count": prop.rooms_count,
        "rooms_details": parsed_rooms,
        "created_at": prop.created_at.isoformat() if prop.created_at else None,
        "updated_at": prop.updated_at.isoformat() if prop.updated_at else None,
        "owner": {
            "id": prop.owner.id,
            "first_name": prop.owner.first_name,
            "last_name": prop.owner.last_name,
        },
    }


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


@bp.get('')
def list_properties():
    """List all properties, optionally filtered by city.
    
    Query Parameters:
        city (str, optional): Filter properties by city name (case-insensitive)
    
    Example:
        GET /properties?city=Paris
    """
    city = request.args.get('city', '').strip()
    
    query = Property.query
    
    if city:
        query = query.filter(func.lower(Property.city) == func.lower(city))
    
    properties = query.order_by(Property.created_at.desc()).all()
    
    return jsonify({"properties": [_serialize_property(p) for p in properties]}), 200


@bp.get('/<int:property_id>')
def retrieve_property(property_id: int):
    """Get a single property by id."""
    prop = Property.query.get(property_id)
    if prop is None:
        return jsonify({"error": "property not found"}), 404
    return jsonify({"property": _serialize_property(prop)}), 200


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

    # Ensure owner exists
    owner = User.query.get(current_user_id)
    if owner is None:
        return jsonify({"error": "owner user not found"}), 400

    # Create new property
    new_property = Property(
        owner_id=current_user_id,
        name=fields['name'],
        description=fields['description'],
        property_type=fields['property_type'],
        city=fields['city'],
        rooms_count=fields['rooms_count'],
        rooms_details=fields['rooms_details']
    )
    
    db.session.add(new_property)
    db.session.commit()
    
    return jsonify({"property": _serialize_property(new_property)}), 201


@bp.route('/<int:property_id>', methods=('PUT', 'PATCH'))
def update_property(property_id: int):
    """Update a property (only owner can edit)."""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({"error": "X-User-Id header is required"}), 401

    prop = Property.query.get(property_id)
    if prop is None:
        return jsonify({"error": "property not found"}), 404

    if prop.owner_id != current_user_id:
        return jsonify({"error": "you can only edit your own properties"}), 403

    payload = request.get_json(silent=True) or {}
    fields, error = _extract_property_payload(payload, partial=True)
    if error:
        return jsonify({"error": error}), 400
    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    # Update fields
    for key, value in fields.items():
        setattr(prop, key, value)
    
    db.session.commit()
    
    return jsonify({"property": _serialize_property(prop)}), 200


@bp.delete('/<int:property_id>')
def delete_property(property_id: int):
    """Delete a property (only owner can delete)."""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({"error": "X-User-Id header is required"}), 401

    prop = Property.query.get(property_id)
    if prop is None:
        return jsonify({"error": "property not found"}), 404

    if prop.owner_id != current_user_id:
        return jsonify({"error": "you can only delete your own properties"}), 403

    db.session.delete(prop)
    db.session.commit()
    
    return jsonify({"message": "property deleted"}), 200