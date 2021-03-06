"""Module for Logged Activities in Andela."""

from flask import g, request, current_app
from flask_restful import Resource
from sqlalchemy import func

from api.models import LoggedActivity, User, db
from api.utils.auth import token_required, roles_required
from api.utils.helpers import (ParsedResult, parse_log_activity_fields,
                               response_builder, paginate_items)
from api.utils.marshmallow_schemas import (
    log_edit_activity_schema, single_logged_activity_schema,
    logged_activities_schema, user_logged_activities_schema
)
from api.utils.notifications.email_notices import send_email


class UserLoggedActivitiesAPI(Resource):
    """User Logged Activities Resources."""

    decorators = [token_required]

    @classmethod
    def get(cls, user_id):
        """Get a user's logged activities by user_id URL parameter."""
        user = User.query.get(user_id)
        if not user:
            return response_builder(dict(message="User not found"), 404)

        message = "Logged activities fetched successfully"
        user_logged_activities = user.logged_activities.all()

        if not user_logged_activities:
            message = "There are no logged activities for that user."

        points_earned = db.session.query(
            func.sum(LoggedActivity.value)
        ).filter(
            LoggedActivity.user_id == user_id,
            LoggedActivity.status == 'approved'
        ).scalar()

        return response_builder(dict(
            data=user_logged_activities_schema.dump(
                user_logged_activities).data,
            society=user.society.name if user.society else None,
            societyId=user.society.uuid if user.society else None,
            activitiesLogged=len(user_logged_activities),
            pointsEarned=points_earned if points_earned else 0,
            message=message
        ), 200)


class LoggedActivitiesAPI(Resource):
    """Logged Activities Resources."""

    decorators = [token_required]

    @classmethod
    def post(cls):
        """Log a new activity."""
        payload = request.get_json(silent=True)

        if payload:
            result, errors = log_edit_activity_schema.load(payload)

            if errors:
                return response_builder(dict(validationErrors=errors), 400)

            society = g.current_user.society
            if not society:
                return response_builder(dict(
                    message='You are not a member of any society yet'
                ), 422)

            parsed_result = parse_log_activity_fields(result)
            if not isinstance(parsed_result, ParsedResult):
                return parsed_result

            # log activity
            logged_activity = LoggedActivity(
                name=result.get('name'),
                description=result.get('description'),
                society=society,
                user=g.current_user,
                activity=parsed_result.activity,
                photo=result.get('photo'),
                value=parsed_result.activity_value,
                activity_type=parsed_result.activity_type,
                activity_date=parsed_result.activity_date
            )

            if logged_activity.activity_type.name == 'Bootcamp Interviews':
                if not result['no_of_participants']:
                    return response_builder(dict(
                                            message="Data for creation must be"
                                                    " provided. (no_of_"
                                                    "participants)"),
                                            400)
                else:
                    logged_activity.no_of_participants = result[
                        'no_of_participants'
                    ]

            logged_activity.save()

            return response_builder(dict(
                data=single_logged_activity_schema.dump(logged_activity).data,
                message='Activity logged successfully'
            ), 201)

        return response_builder(dict(
                                message="Data for creation must be provided."),
                                400)

    @classmethod
    def get(cls):
        """Get all logged activities."""
        paginate = request.args.get("paginate", "true")
        message = "all Logged activities fetched successfully"

        if paginate.lower() == "false":
            logged_activities = LoggedActivity.query.all()
            count = LoggedActivity.query.count()
            data = {"count": count}
        else:
            logged_activities = LoggedActivity.query
            pagination_result = paginate_items(logged_activities,
                                               serialize=False)
            logged_activities = pagination_result.data
            data = {
                "count": pagination_result.count,
                "page": pagination_result.page,
                "pages": pagination_result.pages,
                "previous_url": pagination_result.previous_url,
                "next_url": pagination_result.next_url
            }

        data.update(dict(
            loggedActivities=logged_activities_schema.dump(
                logged_activities
            ).data))

        return response_builder(dict(data=data, message=message,
                                     status="success"), 200)


class LoggedActivityAPI(Resource):
    """Single Logged Activity Resources."""

    decorators = [token_required]

    @classmethod
    def put(cls, logged_activity_id=None):
        """Edit an activity."""
        payload = request.get_json(silent=True)

        if payload:
            log_edit_activity_schema.context = {'edit': True}
            result, errors = log_edit_activity_schema.load(payload)
            log_edit_activity_schema.context = {}

            if errors:
                return response_builder(dict(validationErrors=errors), 400)

            logged_activity = LoggedActivity.query.filter_by(
                uuid=logged_activity_id,
                user_id=g.current_user.uuid).one_or_none()
            if not logged_activity:
                return response_builder(dict(
                    message='Logged activity does not exist'
                ), 404)
            if logged_activity.status != 'in review':
                return response_builder(dict(
                    message='Not allowed. Activity is already in pre-approval.'
                ), 401)
            if not result.get('activity_type_id'):
                result['activity_type_id'] = logged_activity.activity_type_id

            if not result.get('date'):
                result['date'] = logged_activity.activity_date
            parsed_result = parse_log_activity_fields(result)
            if not isinstance(parsed_result, ParsedResult):
                return parsed_result

            # update fields
            logged_activity.name = result.get('name')
            logged_activity.description = result.get('description')
            logged_activity.activity = parsed_result.activity
            logged_activity.photo = result.get('photo')
            logged_activity.value = parsed_result.activity_value
            logged_activity.activity_type = parsed_result.activity_type
            logged_activity.activity_date = parsed_result.activity_date

            logged_activity.save()

            return response_builder(dict(
                data=single_logged_activity_schema.dump(logged_activity).data,
                message='Activity edited successfully'
            ), 200)

        return response_builder(dict(
                                message="Data for creation must be provided."),
                                400)

    @classmethod
    def delete(cls, logged_activity_id=None):
        """Delete a logged activity."""
        logged_activity = LoggedActivity.query.filter_by(
            uuid=logged_activity_id,
            user_id=g.current_user.uuid).one_or_none()

        if not logged_activity:
            return response_builder(dict(
                message='Logged Activity does not exist!'
            ), 404)

        if logged_activity.status != 'in review':
            return response_builder(dict(
                message='You are not allowed to perform this operation'
            ), 403)

        logged_activity.delete()
        return response_builder(dict(), 204)


class SecretaryReviewLoggedActivityAPI(Resource):
    """Enable society secretary to verify logged activities."""

    decorators = [token_required]

    @classmethod
    @roles_required(['society secretary'])
    def put(cls, logged_activity_id):
        """Put method on logged Activity resource."""
        payload = request.get_json(silent=True)

        if 'status' not in payload:
            return response_builder(dict(message='status is required.'),
                                    400)

        logged_activity = LoggedActivity.query.filter_by(
            uuid=logged_activity_id).first()
        if not logged_activity:
            return response_builder(dict(message='Logged activity not found'),
                                    404)

        if not (payload.get('status') in ['pending', 'rejected']):
            return response_builder(dict(message='Invalid status value.'),
                                    400)
        logged_activity.status = payload.get('status')
        logged_activity.save()

        return response_builder(
            dict(data=single_logged_activity_schema.dump(logged_activity).data,
                 message="successfully changed status"),
            200)


class LoggedActivityApprovalAPI(Resource):
    """Allows success-ops to approve at least one Logged Activities."""

    decorators = [token_required]

    @classmethod
    @roles_required(["success ops"])
    def put(cls, logged_activity_id=None):
        """Put method for approving logged Activity resource."""
        # TODO: Adding of redemption points needs to be factored into this
        payload = request.get_json(silent=True)

        if payload:
            logged_activities_ids = payload.get('loggedActivitiesIds', None)

            if logged_activities_ids is None:
                return response_builder(dict(
                    message='loggedActivitiesIds is required'), 400)

            if len(logged_activities_ids) > 20:
                return response_builder(dict(
                    message='Sorry, you can not approve more than 20'
                            ' logged_activities at a go'), 403)

            if not isinstance(logged_activities_ids, list) or \
                    not logged_activities_ids:
                return response_builder(dict(
                    message='A List/Array with at least one logged activity'
                            ' id is needed!'), 400)

            unique_activities_ids = set([])
            for logged_activities_id in logged_activities_ids:
                logged_activities = LoggedActivity.query.get(
                    logged_activities_id
                )
                if logged_activities is None or logged_activities.redeemed \
                    or logged_activities.status in ['rejected', 'in review',
                                                    'approved']:
                    continue
                unique_activities_ids.add(logged_activities)

            if not unique_activities_ids:
                return response_builder(dict(
                    status='failed',
                    message='Invalid logged activities or no pending logged'
                            ' activities in request'),
                    400)
            else:
                for unique_activities_id in list(unique_activities_ids):
                    unique_activities_id.status = 'approved'
                    unique_activities_id.society.total_points = \
                        unique_activities_id

                user_logged_activities = logged_activities_schema.dump(
                    unique_activities_ids).data

                # NOTE: this code works as expected, shipping it out for the
                # MVP further optimization will be done from line 319 - 325
                # using marshmallow
                for user_logged_activity in user_logged_activities:
                    user_logged_activity['society'] = {
                        'id': user_logged_activity['societyId'],
                        'name': user_logged_activity['society']
                    }
                    del user_logged_activity['society']['id']
                    del user_logged_activity['societyId']
                return response_builder(dict(
                    data=user_logged_activities,
                    message='Activity edited successfully'),
                    200)
        else:
            return response_builder(dict(
                message='Data for creation must be provided.'),
                400)


class LoggedActivityRejectionAPI(Resource):
    """Allows success-ops to reject at least one Logged Activities."""

    decorators = [token_required]

    @classmethod
    @roles_required(["success ops"])
    def put(cls, logged_activity_id=None):
        """Put method for rejecting logged activity resource."""
        if logged_activity_id is None:
            return response_builder(dict(
                message='loggedActivitiesIds is required'), 400)

        logged_activity = LoggedActivity.query.filter_by(
            uuid=logged_activity_id).first()

        if not logged_activity:
            return response_builder(dict(message='Logged activity not found'),
                                    404)

        if logged_activity.status == 'pending':
            logged_activity.status = 'rejected'

            user_logged_activity = single_logged_activity_schema.dump(
                logged_activity).data
            user_logged_activity['society'] = {
                'id': user_logged_activity['societyId'],
                'name': user_logged_activity['society']
            }
            del user_logged_activity['societyId']

            return response_builder(dict(
                data=user_logged_activity,
                message='Activity successfully rejected'),
                200)
        else:
            return response_builder(dict(
                status='failed',
                message='This logged activity is either in-review,'
                ' approved or already rejected'), 403)


class LoggedActivityInfoAPI(Resource):
    """Allows success-ops to request more info on a Logged Activity."""

    decorators = [token_required]

    @classmethod
    @roles_required(["success ops"])
    def put(cls, logged_activity_id=None):
        """Put method for requesting more info on a logged activity."""
        payload = request.get_json(silent=True)

        if not payload:
            return response_builder(dict(
                message="Data for editing must be provided",
                status="fail"
            ), 400)

        if not logged_activity_id:
            return response_builder(dict(
                status="fail",
                message="LoggedActivity id must be provided."), 400)

        logged_activity = LoggedActivity.query.get(logged_activity_id)

        if not logged_activity:
            return response_builder(dict(message='Logged activity not found'),
                                    404)

        comment = payload.get("comment")
        if comment:
            send_email.delay(
                sender=current_app.config["SENDER_CREDS"],
                subject="More Info on Logged Activity for {}".format(
                    logged_activity.user.society.name),
                message="Success Ops needs more information on this"
                        " logged activity: {}.\\n Context: {}."
                        "\\nClick <a href='{}'>here</a>"
                        " to view the logged activity and edit the"
                        " description to give more informaton.".format(
                            logged_activity.name, comment, request.host_url +
                            '/api/v1/logged-activities/' +
                            logged_activity.uuid
                ),
                recipients=[logged_activity.user.email]
            )
        else:
            return response_builder(dict(
                status="fail",
                message="Context for extra informaton must be provided."), 400)

        return response_builder(dict(
            status='success',
            message='Extra information has been successfully requested'),
            200)
