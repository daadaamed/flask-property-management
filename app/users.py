from datetime import date

from flask import Blueprint, request, jsonify, abort

from .db import get_db

bp = Blueprint('users', __name__, url_prefix='/users')


@bp.post('')
def create_user():
    """Create a user with first_name, last_name and date_of_birth (YYYY-MM-DD)."""
    data = request.get_json() or {}

    first_name = data.get('first_name')
    last_name = data.get('last_name')
    dob_str = data.get('date_of_birth')

    if not first_name or not last_name or not dob_str:
        return jsonify({'error': 'first_name, last_name and date_of_birth are required'}), 400

    dob = None
    if dob_str:
        try:
            year, month, day = map(int, dob_str.split('-'))
            dob = date(year, month, day)
        except ValueError:
            return jsonify({'error': 'date_of_birth must be YYYY-MM-DD'}), 400

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (first_name, last_name, date_of_birth)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (first_name, last_name, dob),
        )
        user_id = cur.fetchone()['id']
    db.commit()

    return jsonify({'id': user_id}), 201

# read from header a simlation of authentication
def get_current_user_id() -> int | None:
    """Read the current user id from the X-User-Id header (dev-only auth)."""
    raw = request.headers.get('X-User-Id')
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None

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

    data = request.get_json() or {}

    # Only allow updating these fields
    allowed_fields = {'first_name', 'last_name', 'date_of_birth'}
    if not any(field in data for field in allowed_fields):
        return jsonify({'error': 'no supported fields to update'}), 400

    db = get_db()
    with db.cursor() as cur:
        # Fetch current values
        cur.execute(
            """
            SELECT id, first_name, last_name, date_of_birth
            FROM users
            WHERE id = %s;
            """,
            (user_id,),
        )
        row = cur.fetchone()

        if row is None:
            abort(404)

        first_name = data.get('first_name', row['first_name'])
        last_name = data.get('last_name', row['last_name'])

        dob = row['date_of_birth']
        if 'date_of_birth' in data:
            dob_str = data['date_of_birth']
            if dob_str is None:
                dob = None
            else:
                try:
                    year, month, day = map(int, dob_str.split('-'))
                    dob = date(year, month, day)
                except ValueError:
                    return jsonify({'error': 'date_of_birth must be YYYY-MM-DD'}), 400

        # Apply update
        cur.execute(
            """
            UPDATE users
            SET first_name = %s,
                last_name = %s,
                date_of_birth = %s
            WHERE id = %s;
            """,
            (first_name, last_name, dob, user_id),
        )

    db.commit()
    return jsonify({'message': 'user updated'})

@bp.get('')
def list_users():
    """Get a list of all users."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, first_name, last_name, date_of_birth
            FROM users
            ORDER BY id;
            """
        )
        rows = cur.fetchall()

    users = [
        {
            'id': row['id'],
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'date_of_birth': row['date_of_birth'],
        }
        for row in rows
    ]

    return jsonify(users)

@bp.get('/<int:user_id>')
def get_user(user_id: int):
    """Get a single user by id."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, first_name, last_name, date_of_birth
            FROM users
            WHERE id = %s;
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if row is None:
        abort(404)

    return jsonify(
        {
            'id': row['id'],
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'date_of_birth': row['date_of_birth'],
        }
    )
