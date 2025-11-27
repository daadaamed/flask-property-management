import click
import json
import psycopg2
from flask import current_app, g
from flask.cli import with_appcontext 
from psycopg2.extras import RealDictCursor

def get_db():
    if 'db' not in g:
        database_url = current_app.config.get('DATABASE_URL')
        if not database_url:
            raise RuntimeError('DATABASE_URL is not configured.')
        g.db = psycopg2.connect(database_url, cursor_factory=RealDictCursor)

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    from flask import current_app
    with current_app.open_resource('schema.sql') as f:
        schema_sql = f.read().decode('utf8')

    statements = [statement.strip() for statement in schema_sql.split(';') if statement.strip()]
    with db.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
    db.commit()


@click.command('init-db')
@with_appcontext 
def init_db_command():
    """Recreate the database schema defined in schema.sql."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(populate_db_command)
    
def populate_db():
    """
    Insert simple sample data (users + properties).

    - Idempotent-ish: does nothing if users table is not empty.
    - Uses parameterized queries for safety.
    """
    db = get_db()

    with db.cursor() as cur:
        # Only populate if empty
        cur.execute("SELECT COUNT(*) AS count FROM users;")
        if cur.fetchone()["count"] > 0:
            return  # already populated, do nothing

        # --- Insert users ---
        cur.execute(
            """
            INSERT INTO users (first_name, last_name, date_of_birth)
            VALUES
                (%s, %s, %s),
                (%s, %s, %s)
            RETURNING id;
            """,
            (
                "Alice", "Owner", "1990-01-01",
                "Bob", "Landlord", "1985-05-15",
            ),
        )
        users = cur.fetchall()
        alice_id = users[0]["id"]
        bob_id = users[1]["id"]

        # --- Insert properties ---
        properties = [
            {
                "name": "Appartement centre-ville",
                "description": "Super appart proche métro",
                "property_type": "apartment",
                "city": "Paris",
                "rooms_details": [
                    {"name": "chambre", "size": 12},
                    {"name": "salon", "size": 20},
                ],
                "rooms_count": 2,
                "owner_id": alice_id,
            },
            {
                "name": "Maison de campagne",
                "description": "Maison calme avec jardin",
                "property_type": "house",
                "city": "Lyon",
                "rooms_details": [
                    {"name": "chambre", "size": 15},
                    {"name": "salon", "size": 25},
                    {"name": "cuisine", "size": 10},
                ],
                "rooms_count": 3,
                "owner_id": bob_id,
            },
        ]

        for p in properties:
            cur.execute(
                """
                INSERT INTO properties (
                    name, description, property_type, city,
                    rooms_count, rooms_details, owner_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    p["name"],
                    p["description"],
                    p["property_type"],
                    p["city"],
                    p["rooms_count"],
                    json.dumps(p["rooms_details"]),
                    p["owner_id"],
                ),
            )

    db.commit()


@click.command("populate-db")
@with_appcontext
def populate_db_command():
    """Populate the database with sample users and properties."""
    populate_db()
    click.echo("Populated the database with sample data.")