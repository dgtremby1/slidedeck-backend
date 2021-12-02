import http
from flask import Flask, request, abort
from flask_restful import Resource, Api
import database
import os
import sys
from bson import json_util
import json

import export

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask("__name__")
api = Api(app)


def connect_db(test):
    if test:
        api.db = database.Database(True)
        api.token_timeout = 60
    else:
        api.db = database.Database()
        api.token_timeout = int(os.environ.get("TOKEN_TIMEOUT"))
        print(api.token_timeout)


def parse_json(data):
    return json.loads(json_util.dumps(data))


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


class Login(Resource):
    def put(self):
        request_json = request.get_json()
        name = request_json["username"]
        password = request_json["password"]
        if api.db.check_user_exists(name):
            result, user = api.db.check_password(name, password)
            if result:
                return {
                        "result": result,
                        "user": {
                                "role": user["role"],
                                "username": user["username"],
                                "token": api.db.create_token(api.token_timeout, user["id"])
                                }
                        }
            else:
                return {"result": False}
        else:
            return {"result": False}


class Register(Resource):
    def post(self):
        request_json = request.get_json()
        username = request_json["username"]
        password = request_json["password"]
        code = request_json["admin_generated_code"]
        name = request_json["full_name"]
        email = request_json["email"]
        check = api.db.check_user_exists(username)
        print(check)
        if check:
            return {"result": False}
        else:
            result = api.db.create_user(username, password, name, email, code)
            return {"result": result}


class TemplateCreate(Resource):
    def post(self):
        request_json = request.get_json()
        print(request_json)
        token = request_json.get("token")
        user = api.db.check_token(token)
        if user is None:
            return abort(403, "bad token")
        else:
            try:
                return parse_json(api.db.create_template(request_json["name"], request_json["columns"]))
            except Exception as e:
                print(e)
                abort(400, "bad params")


class TemplateList(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            return abort(403, "bad token")
        else:
            return {"result": parse_json(api.db.get_templates())}


class TestCreate(Resource):
    def post(self):
        request_json = request.get_json()
        token = request_json.get("token")
        user = api.db.check_token(token)
        if user is None:
            return abort(403, "bad token")
        else:
            try:
                test = api.db.create_test(request_json["name"], request_json["template"], request_json["fields"])
                if test:
                    return http.HTTPStatus.OK
                else:
                    return http.HTTPStatus.INTERNAL_SERVER_ERROR
            except Exception as e:
                abort(400, "bad params")


class TestList(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            return abort(403, "bad token")
        else:
            return {"result": parse_json(api.db.get_tests())}


class LogCreate(Resource):
    def post(self):
        request_json = request.get_json()
        token = request_json.get("token")
        user = api.db.check_token(token)
        if user is None:
            return abort(403, "bad token")
        else:
            try:
                log = api.db.create_log(request_json["template"],
                                        request_json["presets"],
                                        request_json.get("name"))
                return {"result": parse_json(log)
                        } if log is not None else None

            except KeyError as e:
                return abort(400, "bad params")


class LogGet(Resource):
    def get(self, log_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            return parse_json({"result": api.db.get_log(log_id)})


class LogList(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            return {"result": parse_json(api.db.get_logs())}


class LogSlideGet(Resource):
    def get(self, log_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            try:
                slides = api.db.get_slides(log_id)
                if slides:
                    return parse_json(slides)
                else:
                    return http.HTTPStatus.BAD_REQUEST
            except:
                return http.HTTPStatus.BAD_REQUEST


class PostSlide(Resource):
    def post(self, log_id):
        request_json = request.get_json()
        token = request_json["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            try:
                slide = api.db.post_slide(log_id, request_json["fields"], request_json["submit"], user)
                return{"result": parse_json(slide)} if slide is not None else http.HTTPStatus.INTERNAL_SERVER_ERROR
            except KeyError as e:
                return abort(400, "bad params")


class EditSlide(Resource):
    def put(self, log_id):
        request_json = request.get_json()
        token = request_json["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            try:
                result = api.db.edit_slide(request_json["slide"], request_json["fields"], request_json["submit"], user)
                if result:
                    return http.HTTPStatus.OK
                else:
                    return http.HTTPStatus.BAD_REQUEST
            except KeyError as e:
                return abort(400, "bad params")


class Template(Resource):
    def patch(self, template_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
    def get(self, template_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            try:
                result = api.db.get_template(template_id)
                return parse_json(result) if result is not None else http.HTTPStatus.NOT_FOUND
            except:
                abort(500, "internal server error")

    def delete(self, template_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            try:
                result = api.db.delete_template(template_id)
                return http.HTTPStatus.OK if result else http.HTTPStatus.BAD_REQUEST
            except:
                return abort(500, "internal server error")


class Token(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        return {"result": False if user is None else True}


class SignupCode(Resource):
    def get(self):
        token = request.args["token"]
        length = request.args["expiration_length"]
        role = request.args["role"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        if user["role"] != "admin":
            return http.HTTPStatus.FORBIDDEN()
        else:
            signup_code = api.db.create_signup_code(length*60*60, role)
            return signup_code

class ExportLog(Resource):
    def get(self, log_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            export.export_log(api.db, log_id)
            return http.HTTPStatus.OK

api.add_resource(Login, "/login")
api.add_resource(Register, "/register")
api.add_resource(Token, "/token")
api.add_resource(SignupCode, "/signup")

api.add_resource(TemplateList, "/templates/")
api.add_resource(Template, "/templates/<string:template_id>/")
api.add_resource(TemplateCreate, "/templates/create")
# api.add_resource(TestList, "/tests/")
# api.add_resource(TestCreate, "/tests/create")
api.add_resource(LogList, "/logs/")
api.add_resource(LogCreate, "/logs/create")
api.add_resource(LogGet, "/logs/<string:log_id>/")
api.add_resource(ExportLog, "/logs/<string:log_id>/export/")
api.add_resource(LogSlideGet, "/logs/<string:log_id>/slides/")
api.add_resource(PostSlide, "/logs/<string:log_id>/slides/create")
api.add_resource(EditSlide, "/logs/<string:log_id>/slides/edit")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        connect_db(True)
    else:
        connect_db(False)
    # context = ('server.crt', 'server.key')
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT")))#, ssl_context=context)
else:
    connect_db(False)
