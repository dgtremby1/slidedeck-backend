import unittest
import database
import time
import flask_unittest
from api import app, connect_db
import export

db = database.Database(True)


class ADatabaseTests(unittest.TestCase):
    def test_a_check_user_exists_one(self):
        self.assertFalse(db.check_user_exists("test"))
    def test_b_register(self):
        self.assertTrue(db.create_user("test", "testpassword", "tech"), "user creation failed")
    def test_c_check_user_exists_two(self):
        self.assertTrue(db.check_user_exists("test"))
    def test_d_login(self):
        result, id = db.check_password("test", "testpassword")
        self.assertTrue(result, "failed to login")
        self.assertIsNotNone(id, "id was none")
        result, id = db.check_password("test", "wrongpassword")
        self.assertFalse(result, "logged in with wrong password")
        self.assertIsNone(id, "id was given for wrong password")
        result, id = (db.check_password("userDoesntExist", "whocares"))
        self.assertFalse(result)
        self.assertIsNone(id)
    def test_e_create_token(self):
        result, id = db.check_password("test", "testpassword")
        if result is False:
            self.skipTest("failed to login")
        token = db.create_token(60, id)
        self.assertIsNotNone(token, "token was none")
    def test_f_check_token(self):
        result, user0 = db.check_password("test", "testpassword")
        if result is False:
            self.skipTest("failed to login")
        token = db.create_token(2, user0["id"])
        if token is None:
            self.skipTest("failed to create token")
        user = db.check_token(token)
        self.assertIsNotNone(user, "user was None")
        self.assertEqual(user["name"], "test", "user name was wrong")
        self.assertEqual(user["id"], user0["id"], "user id was wrong")
        self.assertEqual(user["role"], "tech", "user role was wrong")
        user = db.check_token("0000a1")
        self.assertIsNone(user, "user was returned for bad Token")
        time.sleep(2)
        user = db.check_token(token)
        self.assertIsNone(user, "Token worked after timeout")
    def test_g_get_templates_one(self):
        self.assertEqual(db.get_templates(), [])
    def test_h_create_template(self):
        template = db.create_template("test", [{"title":"test1", "type":"string", "role":"tech"}, {"title":"test2", "type":"string", "role":"doc"}])
        self.assertEqual(template["name"], "test")
        self.assertEqual(template["headers"], {"test1": ["string", "tech"], "test2": ["string", "doc"]})
    def test_i_get_templates_two(self):
        self.assertIsNot(db.get_templates(), [])
        templates = db.get_templates()
        self.assertEqual(templates[0]["name"], "test")
        self.assertEqual(templates[0]["headers"], {"test1": ["string", "tech"], "test2": ["string", "doc"]})
    def test_j_get_tests_one(self):
        self.assertEqual(db.get_tests(), [])
    def test_k_create_test(self):
        templates = db.get_templates()
        if not templates:
            self.skipTest("failed to get template")
        self.assertTrue(db.create_test("test",
                                        templates[0]["id"],
                                        [{"name":"test1", "value":"blue"}, {"name":"test2", "value":"green"}]
                                        ))
    def test_l_get_tests_two(self):
        self.assertIsNot(db.get_tests(), [])
        tests = db.get_tests()
        self.assertEqual(tests[0]["name"], "test")
        self.assertEqual(tests[0]["fields"], [{"name":"test1", "value":"blue"}, {"name":"test2", "value":"green"}])
    def test_m_get_logs_one(self):
        self.assertEqual(db.get_logs(), [])
    def test_n_create_and_get_log(self):
        templates = db.get_templates()
        if not templates:
            self.skipTest("failed to get template")
        tests = db.get_tests()
        if not tests:
            self.skipTest("failed to get tests")
        template_id = templates[0]["id"]
        test_id = tests[0]["id"]
        result = db.create_log(template_id, test_id, None)["id"]
        self.assertIsNotNone(result)
        log = db.get_log(result)
        self.assertEqual(log["id"], result)
        self.assertEqual(log["template"], template_id)
        self.assertEqual(log["test"], test_id)
        self.assertEqual(log["name"], "test")
        self.assertEqual(log["slides"], [])
        result = db.create_log(template_id, test_id, "test2")["id"]
        self.assertIsNotNone(result)
        log = db.get_log(result)
        self.assertEqual(log["id"], result)
        self.assertEqual(log["template"], template_id)
        self.assertEqual(log["test"], test_id)
        self.assertEqual(log["name"], "test2")
        self.assertEqual(log["slides"], [])
    def test_o_get_logs_two(self):
        self.assertIsNot(db.get_logs(), [])
        self.assertEqual(len(db.get_logs()), 2)
    def test_pa_post_and_edit_slide(self):
        logs = db.get_logs()
        if not logs:
            self.skipTest("failed to get logs")
        log_id = logs[0]["id"]
        fields = {"test1": "green"}
        result, user0 = db.check_password("test", "testpassword")
        if not result:
            self.skipTest("failed to login")
        token = db.create_token(60, user0["id"])
        user = db.check_token(token)
        if user is None:
            self.skipTest("failed to get user")
        slide_id = db.post_slide(log_id, fields, False, user)["id"]
        self.assertIsNotNone(slide_id)
        self.assertEqual(db.get_logs()[0]["slides"][0], slide_id)
        slide = db.get_slide(slide_id)
        self.assertEqual(slide["fields"]["test1"], "green")
        self.assertFalse(slide["submitted"])
        self.assertTrue(db.edit_slide(slide_id, {"test1": "blue", "test2": "green"}, True, user))
        slide = db.get_slide(slide_id)
        self.assertEqual(slide["fields"]["test1"], "blue")
        self.assertRaises(KeyError, lambda: slide["fields"]["test2"])
    def test_pb_get_slides(self):
        logs = db.get_logs()
        if not logs:
            self.skipTest("failed to get logs")
        log_id = logs[0]["id"]
        slides = db.get_slides(log_id)
        self.assertIsNot(slides, [])
        self.assertEqual(slides[0]["fields"]["test1"], "blue")

class qApiTests(flask_unittest.ClientTestCase):
    app = app

    def setUp(self, client) -> None:
        connect_db(True)

    def test_q_register(self, client):
        response1 = client.post("/register", json={"name":"test", 'password':'testpass', 'role':'tech'})
        self.assertJsonEqual(response1, {"result": True})
        response2 = client.post("/register", json={'name':'test', 'password':"testpass", 'role':'doc'})
        self.assertJsonEqual(response2, {"result": False})
        response1 = client.put("/login", json={"name":"test", "password":"test"})
        self.assertJsonEqual(response1, {"result": False})
        response = client.put("/login", json={"name":"lol", "password":"bad"})
        self.assertJsonEqual(response, {"result": False})
        response2 = client.put("login", json={"name":"test", "password":"testpass"})
        self.assertIsNotNone(response2.json["user"]["token"])
        self.assertTrue(response2.json["result"])
        token = response2.json["user"]["token"]

        templates = client.get(f"/templates/?token=123")
        self.assertStatus(templates, 403)
        templates = client.get(f"/templates/?token={token}")
        self.assertJsonEqual(templates, {"result": []})

        template = client.post("/templates/create", json={"name": "test",
                                                         "columns": [
                                                            {"title":"test1", "type":"string", "role":"tech"},
                                                            {"title":"test2", "type":"string", "role":"doc"}
                                                            ],
                                                         "token": token
                                                         })
        self.assertEqual(template.json["name"], "test")
        self.assertEqual(template.json["headers"], {"test1": ["string", "tech"], "test2": ["string", "doc"]})
        template = client.post("/templates/create", json={"name": "test",
                                                         "columns": [
                                                            {"title":"test1", "type":"string", "role":"tech"},
                                                            {"title":"test2", "type":"string", "role":"doc"}
                                                            ],
                                                         "token": "123"
                                                         })
        self.assertStatus(template, 403)

        template = client.post("/templates/create", json={
                                                         "columns":
                                                            {"title":"test1", "type":"string", "role":"tech"},
                                                         "token": token
                                                         })
        self.assertStatus(template, 400)

        templates = client.get(f"/templates/?token={token}").json["result"]
        self.assertEqual(templates[0]["name"], "test")
        self.assertEqual(templates[0]["headers"], {"test1": ["string", "tech"], "test2": ["string", "doc"]})

        create_test = client.post("/tests/create", json={"name": "test",
                                                        "template": templates[0]["id"],
                                                        "fields": [{"name": "test1", "value": "blue"}, {"name": "test2", "value": "green"}],
                                                        "token": token
                                                        })
        self.assertStatus(create_test, 200)
        create_test = client.post("/tests/create", json={"name": "test",
                                                        "template": templates[0]["id"],
                                                        "fieldasdfs": [{"name": "test1", "value": "blue"}, {"name": "test2", "value": "green"}],
                                                        "token": token
                                                        })
        self.assertStatus(create_test, 400)
        tests = client.get(f"/tests/?token={token}").json["result"]
        self.assertEqual(tests[0]["name"], "test")
        self.assertEqual(tests[0]["fields"], [{"name":"test1", "value":"blue"}, {"name":"test2", "value":"green"}])

        result = client.post("/logs/create", json={"template":  templates[0]["id"], "test": tests[0]["id"], "token":token}).json
        result = result["result"]
        log = client.get(f"/logs/{result['id']}/?token={token}").json["result"]
        self.assertEqual(log["template"], templates[0]["id"])
        self.assertEqual(log["test"], tests[0]["id"])
        self.assertEqual(log["name"], "test")
        self.assertEqual(log["slides"], [])

        logs = client.get(f"/logs/?token={token}").json
        self.assertEqual(len(logs), 1)
        fields = {"test1": "green"}
        slide = client.post(f"/logs/{log['id']}/slides/create", json={"fields": fields, "submit": False, "token":token}).json["result"]
        slide = client.put(f"/logs/{log['id']}/slides/edit", json={"slide": slide["id"], "fields":{"test1": "blue", "test2": "green"}, "submit": True, "token": token})
        self.assertStatus(slide, 200)


        slides = client.get(f"/logs/{log['id']}/slides/?token={token}").json
        self.assertEqual(len(logs), 1)
        self.assertEqual(slides[0]["fields"], {"test1": "blue"})

        export = client.get(f"/logs/{log['id']}/export/?token={token}")

if __name__ == '__main__':
    unittest.main()