"""Main app module."""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_restful import Api

from api.endpoints.activity_types import ActivityTypesAPI
from api.endpoints.activities import ActivitiesAPI
from api.endpoints.societies import SocietyResource, AddCohort
from api.endpoints.redemption_requests import PointRedemptionAPI
from api.endpoints.redemption_requests import RedemptionRequestNumeration
from api.endpoints.redemption_requests import RedemptionRequestFunds
from api.endpoints.users import UserAPI
from api.endpoints.logged_activities import (UserLoggedActivitiesAPI,
                                             SecretaryReviewLoggedActivityAPI)
from api.endpoints.logged_activities import LoggedActivitiesAPI
from api.endpoints.logged_activities import LoggedActivityAPI
from api.endpoints.logged_activities import (LoggedActivityApprovalAPI,
                                             LoggedActivityRejectionAPI,
                                             LoggedActivityInfoAPI)
from api.endpoints.roles import RoleAPI, SocietyRoleAPI
from api.models import db


try:
    from .config import configuration
except ImportError:
    from config import configuration


def create_app(environment="Production"):
    """Factory Method that creates an instance of the app with the given env.

    Args:
        environment (str): Specify the configuration to initilize app with.

    Return:
        app (Flask): it returns an instance of Flask.
    """
    app = Flask(__name__)
    app.config.from_object(configuration[environment])
    db.init_app(app)

    api = Api(app=app)

    # enable cross origin resource sharing
    CORS(app)

    # activities endpoints
    api.add_resource(
        ActivitiesAPI, '/api/v1/activities', '/api/v1/activities/',
        endpoint='activities'
    )

    # activity types endpoints
    api.add_resource(
        ActivityTypesAPI, '/api/v1/activity-types',
        '/api/v1/activity-types/', endpoint='activity_types'
    )

    api.add_resource(
        ActivityTypesAPI,
        '/api/v1/activity-types/<string:act_types_id>',
        '/api/v1/activity-types/<string:act_types_id>/',
        endpoint='activity_types_detail'
    )

    # user logged activities
    api.add_resource(
        LoggedActivitiesAPI,
        '/api/v1/logged-activities', '/api/v1/logged-activities/',
        endpoint='logged_activities'
    )
    api.add_resource(
        LoggedActivityAPI,
        '/api/v1/logged-activities/<string:logged_activity_id>',
        '/api/v1/logged-activities/<string:logged_activity_id>/',
        endpoint='logged_activity'
    )

    api.add_resource(
        UserLoggedActivitiesAPI,
        '/api/v1/users/<string:user_id>/logged-activities',
        '/api/v1/users/<string:user_id>/logged-activities/',
        endpoint='user_logged_activities'
    )

    # society secretary logged Activity endpoint
    api.add_resource(
        SecretaryReviewLoggedActivityAPI,
        '/api/v1/logged-activities/review/<string:logged_activity_id>',
        '/api/v1/logged-activities/review/<string:logged_activity_id>/',
        endpoint='secretary_logged_activity'
    )

    # Success Ops Requesting more informaton on a logged activity
    api.add_resource(
        LoggedActivityInfoAPI,
        '/api/v1/logged-activities/info/<string:logged_activity_id>',
        '/api/v1/logged-activities/info/<string:logged_activity_id>/',
        endpoint='info_on_logged_activity'
    )

    # Success-Ops Approval of LoggedActivities
    api.add_resource(
        LoggedActivityApprovalAPI,
        "/api/v1/logged-activities/approve",
        "/api/v1/logged-activities/approve/",
        endpoint="approve_logged_activities"
    )

    # Success-Ops Rejection of LoggedActivities
    api.add_resource(
        LoggedActivityRejectionAPI,
        "/api/v1/logged-activity/reject/<string:logged_activity_id>",
        "/api/v1/logged-activity/reject/<string:logged_activity_id>/",
        endpoint="reject_logged_activity"
    )

    # user endpoints
    api.add_resource(
        UserAPI,
        '/api/v1/users/<string:user_id>',
        '/api/v1/users/<string:user_id>/',
        endpoint='user_info'
    )

    # society endpoints
    api.add_resource(
        SocietyResource,
        "/api/v1/societies",
        "/api/v1/societies/",
        "/api/v1/societies/<string:society_id>",
        "/api/v1/societies/<string:society_id>/",

        endpoint="society"
    )

    # redemption endpoints
    api.add_resource(
        PointRedemptionAPI, "/api/v1/societies/redeem",
        "/api/v1/societies/redeem/",
        endpoint="point_redemption"
    )

    api.add_resource(
        PointRedemptionAPI, "/api/v1/societies/redeem/<string:redeem_id>",
        "/api/v1/societies/redeem/<string:redeem_id>/",
        endpoint="point_redemption_detail"
    )

    api.add_resource(
        RedemptionRequestNumeration,
        "/api/v1/societies/redeem/verify/<string:redeem_id>",
        "/api/v1/societies/redeem/verify/<string:redeem_id>/",
        endpoint="redemption_numeration"
    )

    api.add_resource(
        RedemptionRequestFunds,
        "/api/v1/societies/redeem/funds/<string:redeem_id>",
        "/api/v1/societies/redeem/funds/<string:redeem_id>/",
        endpoint="redemption_request_funds"
    )

    # Add Cohort to society
    api.add_resource(
        AddCohort, "/api/v1/societies/cohorts"
    )

    # role endpoints
    api.add_resource(
        RoleAPI, "/api/v1/roles", "/api/v1/roles/",
        endpoint="role"
    )

    api.add_resource(
        RoleAPI, "/api/v1/roles/<string:role_query>",
        "/api/v1/roles/<string:role_query>/",
        endpoint="role_detail"
    )

    api.add_resource(
        SocietyRoleAPI, "/api/v1/roles/society-execs",
        "/api/v1/roles/society-execs/",
        endpoint="society_execs_roles"
    )

    # enable health check ping to API
    @app.route('/')
    def health_check_url():
        response = jsonify(dict(message='Welcome to Andela societies API.'))
        response.status_code = 200
        return response

    # handle default 404 exceptions with a custom response
    @app.errorhandler(404)
    def resource_not_found(error):
        response = jsonify(dict(
            error='Not found',
            message='The requested URL was not found on the server.'))
        response.status_code = 404
        return response

    # handle default 500 exceptions with a custom response
    @app.errorhandler(500)
    def internal_server_error(error):
        response = jsonify(dict(
            error='Internal server error',
            message="The server encountered an internal error."))
        response.status_code = 500
        return response

    return app
