import click
from flask import current_app
from flask.cli import with_appcontext


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Drop and recreate all tables."""
    from .models import db
    
    click.echo('Dropping all tables...')
    db.drop_all()
    
    click.echo('Creating all tables...')
    db.create_all()
    
    click.echo('Database initialized.')


@click.command('seed-db')
@with_appcontext
def seed_db_command():
    """Seed the database with sample data."""
    from .models import db, User, Property
    import json
    
    # Create sample users
    user1 = User(first_name='John', last_name='Doe', date_of_birth='1990-01-15')
    user2 = User(first_name='Jane', last_name='Smith', date_of_birth='1985-05-20')
    
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    
    # Create sample properties
    prop1 = Property(
        owner_id=user1.id,
        name='Cozy Apartment',
        description='A beautiful 2-bedroom apartment in the city center',
        property_type='apartment',
        city='Paris',
        rooms_count=2,
        rooms_details=json.dumps([
            {'type': 'bedroom', 'size': 15},
            {'type': 'living_room', 'size': 25}
        ])
    )
    
    prop2 = Property(
        owner_id=user2.id,
        name='Modern House',
        description='Spacious house with garden',
        property_type='house',
        city='Lyon',
        rooms_count=4,
        rooms_details=json.dumps([
            {'type': 'bedroom', 'size': 20},
            {'type': 'bedroom', 'size': 18},
            {'type': 'living_room', 'size': 35},
            {'type': 'kitchen', 'size': 15}
        ])
    )
    
    db.session.add(prop1)
    db.session.add(prop2)
    db.session.commit()
    
    click.echo(f'Seeded database with {User.query.count()} users and {Property.query.count()} properties.')


def init_app(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)