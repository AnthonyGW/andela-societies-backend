"""Entry point for app, contain commands to configure and run the app."""

import os
import sys

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell, prompt_bool

from api.models import Activity, Cohort, Country, Role, Society, User, db
from api.utils.initial_data import production_data, test_data
from app import create_app
from run_tests import test

app = create_app(environment=os.environ.get('APP_SETTINGS', "Development"))
manager = Manager(app)


@manager.command
def drop_database():
    """Drop database tables."""
    if prompt_bool("Are you sure you want to lose all your data"):
        try:
            db.drop_all()
            print("Dropped all tables successfully.")
        except Exception:
            print("Failed, make sure your database server is running!")


@manager.command
def create_database():
    """Create database tables from sqlalchemy models."""
    try:
        db.create_all()
        print("Created tables successfully.")
    except Exception:
        db.session.rollback()
        print("Failed, make sure your database server is running!")


@manager.command
def seed():
    """Seed database tables with initial data."""
    environment = os.getenv("APP_SETTINGS", "Production")
    if environment.lower() in ["production", "staging"] and \
            os.getenv("PRODUCTION_SEED") != "True":
        print("\n\n\t\tYou probably don't wanna do that. Exiting...\n")
        sys.exit()

    data_mapping = {
        "Production": production_data,
        "Development": test_data,
        "Testing": test_data,
        "Staging": production_data
    }

    if environment.lower() in ["production", "staging"]:
        print("Seeding data to DB: NOTE create, migrate and upgrade your DB")
        try:
            db.session.add_all(data_mapping.get(environment))
            return print("Data dumped in DB succefully.")
        except Exception as e:
            db.session.rollback()
            return print("Error occured, database rolledback: ", e)

    else:
        mes = "\n\n\nThis operation will remove all existing data" \
             " and create tables in your database\n" \
             " Type n to skip dropping existing data and tables."

        if os.environ.get('Development') and prompt_bool(mes):
            try:
                db.session.remove()
                db.drop_all()
                db.create_all()
                print("\nTables created succesfully.\n")
            except Exception as e:
                return print("\nError while creating tables: ", e)

        try:
            db.session.add_all(data_mapping.get(environment))
            return print("\n\n\nTables seeded successfully.\n\n\n")
        except Exception as e:
            db.session.rollback()
            return print("\n\n\nFailed:\n", e, "\n\n")


@manager.command
def link_society_cohort(cohort_name, society_name):
    """CLI tool, link cohort with society."""
    with app.app_context():
        cohort = Cohort.query.filter_by(name=cohort_name).first()
        if not cohort:
            return print(
                f'Error cohort by name: {cohort_name} does not exist in DB.')
        if cohort.society:
            prompt_bool('Cohort has society already!\n Do you want to change?')

        society = Society.query.filter_by(name=society_name).first()
        if not society:
            return print(
                f'Error society with name:{society_name} does not exist.')

        society.cohorts.append(cohort)
        if society.save():
            message = f'Cohort:{cohort_name} succefully'
            message += f' added to society:{society_name}'
            return print(message)
        else:
            print('Error something went wrong when saving to DB. :-)')


@manager.command
def tests():
    """Run the tests."""
    test()


def shell():
    """Make a shell/REPL context available."""
    return dict(app=app,
                db=db,
                User=User,
                Society=Society,
                Activity=Activity,
                Country=Country,
                Role=Role,
                Cohort=Cohort)


manager.add_command('shell', Shell(make_context=shell))
migrate = Migrate(app, db)
manager.add_command("db", MigrateCommand)

if __name__ == "__main__":
    manager.run()
