"""Test suite for restriction of endpoints by Role."""

import json
import uuid

from .base_test import BaseTestCase, db


class RoleTestCase(BaseTestCase):
    """Holds tests of roles in authentication."""

    def setUp(self):
        """Setup required roles for hitting Role endpoint in tests."""
        BaseTestCase.setUp(self)
        self.successops_role.save()
        self.fellow_role.save()
        self.finance_role.save()
        self.lf_role.save()
        self.successops_token = {"Authorization":
                                 self.generate_token(
                                  self.test_successops_payload)}

    def test_unauthorised_role(self):
        """Test if unauthorised role can access endpoint."""
        unauthorised_token = self.generate_token(self.test_auth_role_payload)
        new_society = dict(name="Gryffindor",
                           colorScheme="#333333",
                           logo="https://bit.ly/2FE1KI2",
                           photo="https://bit.ly/2js4iAq")

        response = self.client.post('/api/v1/societies',
                                    data=json.dumps(new_society),
                                    headers={"Authorization":
                                             unauthorised_token},
                                    content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 401)

        message = "You're unauthorized to perform this operation"
        response_details = json.loads(response.data)

        self.assertEqual(message, response_details["message"])

    def test_fellow_cannot_create_society(self):
        """Test if Fellow role can access Society endpoint."""
        new_society = dict(name="Gryffindor",
                           colorScheme="#333333",
                           logo="https://bit.ly/2FE1KI2",
                           photo="https://bit.ly/2js4iAq")

        response = self.client.post('/api/v1/societies',
                                    data=json.dumps(new_society),
                                    headers=self.header,
                                    content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 401)

        message = "You're unauthorized to perform this operation"
        response_details = json.loads(response.data)

        self.assertEqual(message, response_details["message"])

    def test_successops_can_create_society(self):
        """Test if success ops role can access Society endpoint."""
        new_society = dict(name="Gryffindor",
                           colorScheme="#333333",
                           logo="https://bit.ly/2FE1KI2",
                           photo="https://bit.ly/2js4iAq")

        response = self.client.post('/api/v1/societies',
                                    data=json.dumps(new_society),
                                    headers=self.successops_token,
                                    content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 201)

        message = "Society created successfully"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_create_role(self):
        """Test if role can be created."""
        new_role = dict(name="Society President Test")

        response = self.client.post("/api/v1/roles",
                                    data=json.dumps(new_role),
                                    headers=self.successops_token,
                                    content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 201)

        message = "Role created successfully"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_create_existing_role(self):
        """Test if role can be created."""
        new_role = dict(name="success ops")

        response = self.client.post("/api/v1/roles",
                                    data=json.dumps(new_role),
                                    headers=self.successops_token,
                                    content_type='application/json')

        self.assertTrue(json.loads(response.data))

        message = "Role already exists"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 409)

    def test_get_role_by_id(self):
        """Test that existing role can be retrieved by ID."""
        response = self.client.get("/api/v1/roles/-KXGy1EB1oimjQgFim6L",
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 200)

        message = "fetched successfully"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_get_role_by_name(self):
        """Test that existing role can be retrieved by name."""
        response = self.client.get(f"/api/v1/roles?q={self.fellow_role.name}",
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))

        message = "fetched successfully"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 200)

    def test_get_all_roles(self):
        """Test that all existing roles can be retrieved."""
        response = self.client.get("/api/v1/roles",
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 200)

        message = "fetched successfully"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_edit_role_by_id(self):
        """Test if existing role can be edited by ID."""
        edited_role = dict(name="Number Cruncher")

        response = self.client.put(f"/api/v1/roles/{self.lf_role.uuid}",
                                   data=json.dumps(edited_role),
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 200)

        message = "been changed to"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_edit_no_change_role(self):
        """Test if existing role can be edited."""
        edited_role = dict(name="Learning Facilitator")

        response = self.client.put(f"/api/v1/roles/{self.lf_role.uuid}",
                                   data=json.dumps(edited_role),
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 200)

        message = "No change specified"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_edit_no_name(self):
        """Test if existing role can be edited."""
        edited_role = dict(change="Learning Facilitator")

        response = self.client.put(f"/api/v1/roles/{self.lf_role.uuid}",
                                   data=json.dumps(edited_role),
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 400)

        message = "must be provided"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_edit_nonexistent_role(self):
        """Test if existing role can be edited by ID."""
        edited_role = dict(name="Number Cruncher")

        response = self.client.put(f"/api/v1/roles/{str(uuid.uuid4())}",
                                   data=json.dumps(edited_role),
                                   headers=self.successops_token,
                                   content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 404)

        message = "does not exist"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])

    def test_delete_role(self):
        """Test if existing role can be deleted."""
        response = self.client.delete(f"/api/v1/roles/{self.lf_role.uuid}",
                                      headers=self.successops_token,
                                      content_type='application/json')

        self.assertTrue(json.loads(response.data))
        self.assertEqual(response.status_code, 200)

        message = "deleted"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])


class RoleTestCaseEmpty(BaseTestCase):
    """Test case for no roles in DB."""

    def setUp(self):
        """Set up all needed variables."""
        BaseTestCase.setUp(self)

    def test_get_all_roles_empty(self):
        """Test lack of roles in system is returned."""
        db.drop_all()
        db.create_all()

        response = self.client.get("api/v1/roles",
                                   headers=self.header,
                                   content_type='application/json')

        message = "Resources were not found"
        response_details = json.loads(response.data)
        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 404)


class SocietyRoleTestCase(BaseTestCase):
    """Contains all tests on society roles."""

    def setUp(self):
        """Set up all needed variables."""
        BaseTestCase.setUp(self)
        self.successops_role.save()
        self.president_role.save()
        self.v_president_role.save()
        self.secretary_role.save()
        self.successops_token = {"Authorization":
                                 self.generate_token(
                                  self.test_successops_payload)}
        self.president.roles.append(self.president_role)
        self.president.save()
        self.vice_president.roles.append(self.v_president_role)
        self.vice_president.save()
        self.secretary.roles.append(self.secretary_role)
        self.secretary.save()
        self.test_user.save()
        self.test_user_2.save()
        self.test_user_3.save()

    def test_reassign_society_president(self):
        """Test the appointment of new President."""
        new_president = dict(name="Test User",
                             society="Phoenix",
                             role="society president")

        response = self.client.put("/api/v1/roles/society-execs",
                                   data=json.dumps(new_president),
                                   headers=self.successops_token,
                                   content_type='application/json')

        message = "has been appointed"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 200)

    def test_reassign_society_vice_president(self):
        """Test the appointment of new Vice President."""
        new_vice_president = dict(name="Test User",
                                  society="Sparks",
                                  role="vice president")

        response = self.client.put("/api/v1/roles/society-execs",
                                   data=json.dumps(new_vice_president),
                                   headers=self.successops_token,
                                   content_type='application/json')

        message = "has been appointed"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 200)

    def test_reassign_society_secretary(self):
        """Test the appointment of new Secretary."""
        new_secretary = dict(name="Test User",
                             society="Invictus",
                             role="secretary")

        response = self.client.put("/api/v1/roles/society-execs",
                                   data=json.dumps(new_secretary),
                                   headers=self.successops_token,
                                   content_type='application/json')

        message = "has been appointed"
        response_details = json.loads(response.data)

        self.assertIn(message, response_details["message"])
        self.assertEqual(response.status_code, 200)
