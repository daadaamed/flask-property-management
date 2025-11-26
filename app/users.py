from datetime import date

from flask import Blueprint, request, jsonify

from .models import db, User

bp = Blueprint('users', __name__, url_prefix='/users')


def get_current_user_id() -> int | None:
    """Read the current user id from the X-User-Id header (dev-only auth)."""
    raw = request.headers.get('X-User-Id')
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@bp.post('')
def create_user():
    """Create a user with first_name, last_name and date_of_birth (YYYY-MM-DD)."""
    data = request.get_json() or {}

    first_name = data.get('first_name')
    last_name = data.get('last_name')
    dob_str = data.get('date_of_birth')

    if not first_name or not last_name or not dob_str:
        return jsonify({'error': 'first_name, last_name and date_of_birth are required'}), 400

    # Validate date format
    if dob_str:
        try:
            year, month, day = map(int, dob_str.split('-'))
            date(year, month, day)  # Validate the date
        except ValueError:
            return jsonify({'error': 'date_of_birth must be YYYY-MM-DD'}), 400

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob_str
    )
    
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'id': new_user.id}), 201


@bp.patch('/<int:user_id>')
def update_user(user_id: int):
    """
    Update a user, but only if the caller is the same user.
    The caller must send X-User-Id header matching user_id.
    """
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return jsonify({'error': 'X-User-Id header is required'}), 401

    if current_user_id != user_id:
        return jsonify({'error': 'forbidden: you can only update your own user'}), 403

    user = User.query.get(user_id)
    if user is None:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json() or {}

    # Only allow updating these fields
    allowed_fields = {'first_name', 'last_name', 'date_of_birth'}
    if not any(field in data for field in allowed_fields):
        return jsonify({'error': 'no supported fields to update'}), 400

    # Update fields if provided
    if 'first_name' in data:
        user.first_name = data['first_name']
    
    if 'last_name' in data:
        user.last_name = data['last_name']
    
    if 'date_of_birth' in data:
        dob_str = data['date_of_birth']
        if dob_str is None:
            user.date_of_birth = None
        else:
            try:
                year, month, day = map(int, dob_str.split('-'))
                date(year, month, day)  # Validate the date
                user.date_of_birth = dob_str
            except ValueError:
                return jsonify({'error': 'date_of_birth must be YYYY-MM-DD'}), 400

    db.session.commit()
    return jsonify({'message': 'user updated'})


@bp.get('')
def list_users():
    """Get a list of all users."""
    users = User.query.order_by(User.id).all()
    return jsonify([user.to_dict() for user in users])


@bp.get('/<int:user_id>')
def get_user(user_id: int):
    """Get a single user by id."""
    user = User.query.get(user_id)
    if user is None:
        return jsonify({'error': 'user not found'}), 404
    
    return jsonify(user.to_dict())