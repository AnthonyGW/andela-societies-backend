"""RedemptionRequest Module."""

from flask import g, request
from flask_restplus import Resource

from api.utils.auth import roles_required, token_required
from api.utils.helpers import find_item, response_builder
from api.utils.marshmallow_schemas import basic_info_schema, redemption_schema

from ..models import Country, RedemptionRequest, Society


def redemption_paginate(data, society=None):
    society_redemp_list = []
    for redmption in data:
        data, _ = redemption_schema.dump(redmption)
        data["center"], _ = basic_info_schema.dump(redmption.country)
        data['society'], _ = basic_info_schema.dump(redmption.society)
        society_redemp_list.append(data)

    mes = 'fetched successfully'
    return response_builder(dict(
        status="success",
        data=society_redemp_list,
        message=mes
    ), 200)


class PointRedemptionAPI(Resource):
    """
    Resource handling all point redemption requests.

    Only made by society presidents.
    """

    @classmethod
    @token_required
    @roles_required(["society president"])
    def post(cls):
        """Create Redemption Request."""
        payload = request.get_json(silent=True)
        if not payload:
            return response_builder(dict(
                message="Redemption request must have data.",
                status="fail"
            ), 400)

        name = payload.get("reason")
        value = payload.get("value")
        country_input = payload.get("center")

        country = Country.query.filter_by(name=country_input).first()

        if name and value and country_input:
            redemp_request = RedemptionRequest(
                name=name,
                value=value,
                user=g.current_user,
                country=country,
                society=g.current_user.society
            )
            redemp_request.save()
            data, _ = redemption_schema.dump(redemp_request)
            data["center"], _ = basic_info_schema.dump(country)

            return response_builder(dict(
                message="Redemption request created. success ops will be in"
                        " touch soon.",
                status="success",
                data=data
            ), 201)

        else:
            return response_builder(dict(
                message="Redemption request name, value and country required",
                status="fail"
            ), 400)

    @classmethod
    @token_required
    @roles_required(["society president", "success ops"])
    def put(cls, redeem_id=None):
        """Edit Redemption Requests."""
        payload = request.get_json(silent=True)
        if not payload:
            return response_builder(dict(
                message="Data for editing must be provided",
                status="fail"
            ), 400)

        if not redeem_id:
            return response_builder(dict(
                status="fail",
                message="Redemption Request to be edited must be provided"),
                400)

        redemp_request = RedemptionRequest.query.filter_by(
                            uuid=redeem_id).first()
        if not redemp_request:
            return response_builder(dict(
                                status="fail",
                                message="RedemptionRequest does not exist."),
                                404)

        name = payload.get("name")
        value = payload.get("value")
        desc = payload.get("description")

        if name:
            redemp_request.name = name
        if value:
            redemp_request.value = value
        if desc:
            redemp_request.description = desc

        redemp_request.save()

        return response_builder(dict(
            data=redemp_request.serialize(),
            status="success",
            message="RedemptionRequest edited successfully."
        ), 200)

    @classmethod
    @token_required
    @roles_required(["cio", "society president", "vice president", "secretary"])
    def get(cls, redeem_id=None):
        """Get Redemption Requests."""
        if redeem_id:
            redemp_request = RedemptionRequest.query.get(redeem_id)
            return find_item(redemp_request)
        else:
            search_term_name = request.args.get('society')
            if search_term_name:
                society = Society.query.filter_by(
                                        name=search_term_name).first()
                if not society:
                    mes = f"Society with name:{search_term_name} not found"
                    return {"message": mes}, 400

                redemp_request = RedemptionRequest.query.filter_by(
                                                society_id=society.uuid).all()

                return redemption_paginate(redemp_request, society)

            search_term_status = request.args.get('status')
            if search_term_status:
                redemp_request = RedemptionRequest.query.filter_by(
                                        status=search_term_status)
                return redemption_paginate(redemp_request)

            search_term_name = request.args.get('name')
            if search_term_name:
                redemp_request = RedemptionRequest.query.filter_by(
                                        name=search_term_name)
                return redemption_paginate(redemp_request)

            search_term_country = request.args.get("country")
            if search_term_country:
                country_query = Country.query.filter_by(
                            name=search_term_country).first()
                if not country_query:
                    mes = f"country with name:{search_term_name} not found"
                    return {"message": mes}, 400

                redemp_request = RedemptionRequest.query.filter_by(
                                        country=country_query)
                return redemption_paginate(redemp_request)

        redemption_requests = RedemptionRequest.query
        return redemption_paginate(redemption_requests)

    @classmethod
    @token_required
    @roles_required(["success ops", "society president"])
    def delete(cls, redeem_id=None):
        """Delete Redemption Requests."""
        if not redeem_id:
            return response_builder(dict(
                status="fail",
                message="RedemptionRequest id must be provided."), 400)

        redemp_request = RedemptionRequest.query.get(redeem_id)
        if not redemp_request:
            return response_builder(dict(
                status="fail",
                message="RedemptionRequest does not exist."), 404)

        redemp_request.delete()
        return response_builder(dict(
                status="success",
                message="RedemptionRequest deleted successfully."), 200)


class PointRedemptionRequestNumeration(Resource):
    """
    Approve or reject Redemption Requests.

    After approval or rejection the relevant society get the result of the
    request reflects on the amount of points.
    Only done by success ops.
    """

    @classmethod
    @token_required
    @roles_required(["success ops", "cio"])
    def put(cls, redeem_id=None):
        """Approve or Reject Redemption requests."""
        payload = request.get_json(silent=True)
        if not payload:
            return response_builder(dict(
                message="Data for editing must be provided",
                status="fail"
            ), 400)

        if not redeem_id:
            return response_builder(dict(
                status="fail",
                message="RedemptionRequest id must be provided."), 400)

        try:
            status = payload["status"]
        except KeyError as e:
            return response_builder(dict(
                module="RedemptionRequest Module",
                errors=e,
                message="Missing fields"), 400)

        redemp_request = RedemptionRequest.query.get(redeem_id)
        if not redemp_request:
            return response_builder(dict(
                data=None,
                status="fail",
                message="Resource does not exist."
            ), 404)

        if status == "approved":
            user = redemp_request.user
            society = Society.query.get(user.society_id)
            society.used_points = redemp_request
            redemp_request.status = status
        else:
            redemp_request.status = status

        return response_builder(dict(
            message="RedemptionRequest status changed to {}".format(
                                                        redemp_request.status),
            status="success",
            data=redemp_request.serialize()
        ), 200)
