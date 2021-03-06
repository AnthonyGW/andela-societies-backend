"""Contain All App Models."""
import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

db = SQLAlchemy()


def generate_uuid():
    """Generate unique string."""
    return str(uuid.uuid1())


def camel_case(snake_str):
    """Convert string to camel case."""
    title_str = snake_str.title().replace("_", "")

    return title_str[0].lower() + title_str[1:]


# many to many relationship between users and activities
user_activity = db.Table('user_activity',
                         db.Column('user_uuid', db.String,
                                   db.ForeignKey('users.uuid'), nullable=False
                                   ),
                         db.Column('activity_uuid', db.String,
                                   db.ForeignKey('activities.uuid'),
                                   nullable=False))
user_role = db.Table('user_role',
                     db.Column('user_uuid', db.String,
                               db.ForeignKey('users.uuid'), nullable=False
                               ),
                     db.Column('role_uuid', db.String,
                               db.ForeignKey('roles.uuid'),
                               nullable=False))


class Base(db.Model):
    """Base model, contain utility methods and properties."""

    __abstract__ = True
    uuid = db.Column(db.String, primary_key=True, default=generate_uuid)
    name = db.Column(db.String)
    photo = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    description = db.Column(db.String)

    def __repr__(self):
        """Repl rep of models."""
        return f"{type(self).__name__}(id='{self.uuid}', name='{self.name}')"

    def __str__(self):
        """Return string representation."""
        return self.name

    def save(self):
        """Save the object in DB.

        Return:
            saved(boolean) true if saved, false otherwise
        """
        try:
            db.session.add(self)
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
            return False

    def delete(self):
        """Delete the object in DB.

        Return
            deleted(boolean) True if deleted else false
        """
        deleted = None
        try:
            db.session.delete(self)
            db.session.commit()
            deleted = True
        except Exception:
            deleted = False
            db.session.rollback()
        return deleted

    def serialize(self):
        """Map model to a dictionary representation.

        Return:
            A dict object
        """
        dictionary_mapping = {
            camel_case(attribute.name): str(getattr(self, attribute.name))
            if not isinstance(getattr(self, attribute.name), int)
            else getattr(self, attribute.name)
            for attribute in self.__table__.columns
        }
        return dictionary_mapping


class Center(Base):
    """Models different centres in Andela."""

    __tablename__ = 'centers'
    members = db.relationship('User',
                              backref='center',
                              lazy='dynamic',
                              cascade="all, delete, delete-orphan")
    cohorts = db.relationship('Cohort',
                              backref='center',
                              lazy='dynamic',
                              cascade="all, delete, delete-orphan")
    redemption_requests = db.relationship(
        'RedemptionRequest', backref='center', lazy='dynamic',
        order_by='desc(RedemptionRequest.created_at)'
    )


class Cohort(Base):
    """Models cohorts available in Andela."""

    __tablename__ = 'cohorts'
    center_id = db.Column(db.String, db.ForeignKey('centers.uuid'),
                          nullable=False)
    society_id = db.Column(db.String, db.ForeignKey('societies.uuid'))

    members = db.relationship('User', backref='cohort')


class User(Base):
    """Models Users."""

    __tablename__ = 'users'
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)

    society_id = db.Column(db.String, db.ForeignKey('societies.uuid'))
    center_id = db.Column(db.String, db.ForeignKey('centers.uuid'))
    cohort_id = db.Column(db.String, db.ForeignKey('cohorts.uuid'))

    logged_activities = db.relationship(
        'LoggedActivity', backref='user', lazy='dynamic',
        order_by='desc(LoggedActivity.created_at)'
    )
    created_activities = db.relationship('Activity',
                                         backref='added_by',
                                         lazy='dynamic')
    activities = db.relationship('Activity',
                                 secondary='user_activity',
                                 lazy='dynamic',
                                 backref='participants')
    redemption_requests = db.relationship(
        'RedemptionRequest', backref='user', lazy='dynamic',
        order_by='desc(RedemptionRequest.created_at)'
    )


class Role(Base):
    """Models Roles to which all Andelans have."""

    __tablename__ = 'roles'
    users = db.relationship('User', secondary='user_role', lazy='dynamic',
                            backref=db.backref('roles', lazy='dynamic'))


class Society(Base):
    """Model Societies in Andela."""

    __tablename__ = 'societies'
    name = db.Column(db.String, nullable=False, unique=True)
    color_scheme = db.Column(db.String)
    logo = db.Column(db.String)
    _total_points = db.Column(db.Integer, default=0)
    _used_points = db.Column(db.Integer, default=0)

    members = db.relationship('User', backref='society', lazy='dynamic')
    logged_activities = db.relationship('LoggedActivity', backref='society',
                                        lazy='dynamic')
    cohorts = db.relationship('Cohort', backref='society', lazy='dynamic')
    redemptions = db.relationship('RedemptionRequest', backref='society',
                                  lazy='dynamic')

    @property
    def total_points(self):
        """Keep track of all society points."""
        return self._total_points

    @total_points.setter
    def total_points(self, point):
        self._total_points += point.value

    @property
    def used_points(self):
        """Keep track of redeemed points."""
        return self._used_points

    @used_points.setter
    def used_points(self, redemption_request):
        self._used_points += redemption_request.value

    @property
    def remaining_points(self):
        """Keep track of points available for redeemption."""
        return self.total_points - self.used_points


class ActivityType(Base):
    """Models activity types."""

    __tablename__ = 'activity_types'
    value = db.Column(db.Integer, nullable=False)
    supports_multiple_participants = db.Column(db.Boolean, default=False)

    activities = db.relationship('Activity', backref='activity_type')


class Activity(Base):
    """Model activities available for points."""

    __tablename__ = 'activities'
    activity_type_id = db.Column(db.String,
                                 db.ForeignKey('activity_types.uuid'),
                                 nullable=False)
    activity_date = db.Column(db.Date)
    added_by_id = db.Column(db.String,
                            db.ForeignKey('users.uuid'), nullable=False)


class LoggedActivity(Base):
    """Models Activities logged by fellows."""

    __tablename__ = 'logged_activities'
    value = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, default='in review')
    approved_at = db.Column(db.DateTime)
    activity_date = db.Column(db.Date)
    redeemed = db.Column(db.Boolean, nullable=False, default=False)
    no_of_participants = db.Column(db.Integer)

    approver_id = db.Column(db.String)
    reviewer_id = db.Column(db.String)
    activity_type_id = db.Column(
        db.String, db.ForeignKey('activity_types.uuid'), nullable=False
    )
    user_id = db.Column(db.String, db.ForeignKey('users.uuid'), nullable=False)
    society_id = db.Column(
        db.String, db.ForeignKey('societies.uuid'), nullable=False,
    )
    activity_id = db.Column(db.String, db.ForeignKey('activities.uuid'))

    activity = db.relationship('Activity', uselist=False)
    activity_type = db.relationship('ActivityType', uselist=False)


class RedemptionRequest(Base):
    """Model all redemption requests by Society Presidents."""

    __tablename__ = 'redemptions'
    user_id = db.Column(db.String, db.ForeignKey('users.uuid'), nullable=False)
    society_id = db.Column(db.String, db.ForeignKey('societies.uuid'),
                           nullable=False)
    value = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, default="pending", nullable=False)
    center_id = db.Column(db.String, db.ForeignKey('centers.uuid'),
                          nullable=False)
    comment = db.Column(db.String)
    rejection = db.Column(db.String)
