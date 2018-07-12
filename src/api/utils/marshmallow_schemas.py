"""Validation schemas."""
from datetime import date

from marshmallow import (Schema, ValidationError, fields, post_load, validate,
                         validates, validates_schema)

from api.models import Activity, ActivityType, Role, User


class BaseSchema(Schema):
    """Creates a base validation schema."""

    uuid = fields.String(dump_only=True, dump_to='id',
                         validate=[validate.Length(max=36)])
    name = fields.String(
        required=True,
        error_messages={
            'required': {'message': 'A name is required.'}
        })
    photo = fields.String()
    created_at = fields.DateTime(
        dump_only=True, dump_to='createdAt', load_from='createdAt'
    )
    modified_at = fields.DateTime(
        dump_only=True, dump_to='modifiedAt', load_from='modifiedAt'
    )
    description = fields.String()


class RoleSchema(BaseSchema):
    """Create a validation schema for Roles."""

    @post_load
    def verify_role(self, data):
        """Extra validation of roles."""
        existing_role = Role.query.filter(
            Role.name.ilike(data['name'])).first()

        if existing_role:
            self.context = {'status_code': 409}
            raise ValidationError({'message': 'Role already exists!'})


class ActivityTypesSchema(BaseSchema):
    """Creates a validation schema for activity types."""

    description = fields.String(
        required=True,
        error_messages={
            'message': 'A description is required.'
        }
    )
    value = fields.Integer(
        required=True,
        error_messages={
            'message': 'Please send the activity points value'
        }
    )

    supports_multiple_participants = fields.Integer(
        error_messages={
            'message': 'Please send value if activity supports multiple participants'
        },
        dump_to='supportsMultipleParticipants'
    )

    @post_load
    def verify_activity_type(self, data):
        """Extra validation of activity type."""
        existing_activity_type_name = ActivityType.query.filter(
            ActivityType.name.ilike(data['name'])).first()

        if existing_activity_type_name:
            self.context = {'status_code': 409}
            raise ValidationError({'message':
                                   'Activity Type (name) already exists!'})


class LoggedActivitySchema(BaseSchema):
    """Creates a validation schema for logged activities."""

    status = fields.String()
    points = fields.Integer(attribute='value')
    date = fields.Date(attribute='activity_date')
    user = fields.String(attribute='user.name')
    activity_id = fields.String(dump_to='activityId', load_from='activityId')
    activity = fields.String(attribute='activity.name')
    category = fields.String(attribute='activity_type.name')
    redeemed = fields.Boolean()
    activity_type_id = fields.String(
        load_from='activityTypeId', dump_to='activityTypeId'
    )
    no_of_participants = fields.Integer(load_from='noOfParticipants', dump_to='noOfParticipants')
    society_id = fields.String(dump_to='societyId', load_from='societyId')
    society = fields.String(attribute='society.name')
    approved_by = fields.Method(
        'get_approver', dump_to='approvedBy', load_from='approvedBy'
    )
    reviewed_by = fields.Method(
        'get_reviewer', dump_to='reviewedBy', load_from='reviewedBy'
    )

    @staticmethod
    def get_approver(obj):
        """Get approver name."""
        if obj.approver_id:
            approver = User.query.get(obj.approver_id)
            return approver.name
        return

    @staticmethod
    def get_reviewer(obj):
        """Get reviewer name."""
        if obj.reviewer_id:
            reviewer = User.query.get(obj.reviewer_id)
            return reviewer.name
        return


class ActivitySchema(BaseSchema):
    """Creates a validation schema for activities."""

    description = fields.String(
        required=True,
        error_messages={
            'required': {'message': 'A description is required.'}
        })
    activity_type_id = fields.String(
        required=True, load_from='activityTypeId', dump_to='activityTypeId',
        validate=validate.Length(equal=36,
                                 error='The id provided is not valid.'),
        error_messages={
            'required': {'message': 'An activity type ID is required.'}
        })
    activity_date = fields.Date(
        required=True, dump_to='activityDate', load_from='activityDate',
        error_messages={
                'required': {'message': 'An activity date is required.'}
        })
    added_by_id = fields.String(
        dump_only=True, dump_to='addedById', load_from='addedById'
    )

    @post_load
    def verify_activity(self, data):
        """Extra validation for the Activity Schema."""
        invalid_activity_names = ['Blog', 'App', 'Open Source']
        activity_type = ActivityType.query.get(data['activity_type_id'])
        existing_activity = Activity.query.filter(
            Activity.name.ilike(data['name'])).first()

        if not activity_type or activity_type.name in invalid_activity_names:
            self.context = {'status_code': 404}
            raise ValidationError(
                {'activity_type_id':
                 'Activity type does not exist or is unsupported.'})

        if existing_activity:
            self.context = {'status_code': 409}
            raise ValidationError({'name': 'Activity already exists!'})

        if any(name in data['name'] for name in invalid_activity_names):
            raise ValidationError({'name': 'This is not a valid activity!'})

    @validates('activity_date')
    def validates_activity_date(self, value):
        """Validate the activity date field."""
        if value < date.today():
            raise ValidationError(
                {'message':
                 'Date is in the past! Please enter a valid date.'})
        else:
            return value


class LogEditActivitySchema(BaseSchema):
    """Validation Schema for LoggedActivity."""

    name = fields.String(required=False)
    activity_id = fields.String(
        validate=[validate.Length(max=36)], load_from='activityId'
    )
    activity_type_id = fields.String(
        validate=[validate.Length(max=36)], load_from='activityTypeId'
    )
    date = fields.Date()
    no_of_participants = fields.Integer(load_from='noOfParticipants')

    @validates_schema
    def validate_logged_activity(self, data):
        """Validate the logged activity."""
        if (data.get('activity_type_id') and data.get('activity_id')) or not \
                data.get('activity_type_id') and not data.get('activity_id'):
            raise ValidationError(
                'Please send either an activityTypeId or an activityId only',
                'error'
            )

        if data.get('activity_type_id') and not(data.get('date')
                                                and data.get('description')):
            raise ValidationError(
                'Please send a date and description', 'error'
            )

        # NOTE: The following part allows for users to log their own
        # activities when an activity has not been added by an
        # authorized person. When adding activities for hackathons,
        # bootcamps, tech events etc is made a requirement, it should
        # be removed so that only supported activity types are logged
        # via activity_type_id
        multi_participant_activities = [x.uuid for x in ActivityType.query.filter_by(
            supports_multiple_participants=True).all()]
        if data.get('activity_type_id') in multi_participant_activities \
                and not data.get('no_of_participants'):
            raise ValidationError(
                'Please send all required fields for this activity'
                ' i.e. a date, number of participants and a description',
                'no_of_participants'
            )


class CohortSchema(BaseSchema):
    """Validation Schema for Cohort."""

    country_id = fields.String(dump_only=True, dump_to='countryId',
                               validate=[validate.Length(max=36)])

    society_id = fields.String(dump_only=True, dump_to='societyId',
                               validate=[validate.Length(max=36)])


class SocietySchema(BaseSchema):
    """Validation/Serialize Schema for Society."""

    _total_points = fields.String(dump_only=True, dump_to='totalPoints',
                                  validate=[validate.Length(max=36)])

    _used_points = fields.String(dump_only=True, dump_to='usedPoints',
                                 validate=[validate.Length(max=36)])

    remaining_points = fields.String(dump_only=True, dump_to='remainingPoints',
                                     validate=[validate.Length(max=36)])

    color_scheme = fields.String(dump_only=True, dump_to='colorScheme',
                                 validate=[validate.Length(max=36)])


class UserSchema(BaseSchema):
    """User serializer/validator."""

    society_id = fields.String(dump_only=True, dump_to='societyId',
                               validate=[validate.Length(max=36)])
    country_id = fields.String(dump_only=True, dump_to='countryId',
                               validate=[validate.Length(max=36)])
    cohort_id = fields.String(dump_only=True, dump_to='cohortId',
                              validate=[validate.Length(max=36)])


class RedemptionSchema(BaseSchema):
    """Redemption serializer/validator."""

    status = fields.String(dump_only=True, dump_to='status',
                           validate=[validate.Length(max=36)])
    value = fields.Integer(dump_only=True, dump_to='value',
                          validate=[validate.Length(max=36)])


activity_types_schema = ActivityTypesSchema(many=True)
new_activity_type_schema = ActivityTypesSchema()
activity_schema = ActivitySchema()
single_logged_activity_schema = LoggedActivitySchema()
log_edit_activity_schema = LogEditActivitySchema()
user_logged_activities_schema = LoggedActivitySchema(
    many=True, exclude=('society', 'society_id')
)
role_schema = RoleSchema()
cohort_schema = CohortSchema()
base_schema = BaseSchema()
user_schema = UserSchema()
basic_info_schema = BaseSchema()
society_schema = SocietySchema()
redemption_schema = RedemptionSchema()
