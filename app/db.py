import click
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
