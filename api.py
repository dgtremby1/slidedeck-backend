import http
from flask import Flask, request, abort, make_response
from flask.json import dumps
from flask_restful import Resource, Api
import database
import os
import sys
from bson import json_util
import json
import datetime
import export
from notifications import Notifier

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask("__name__")
api = Api(app)


@api.representation("application/octet-stream")
def output_file(data, code, headers=None):
    response = make_response(dumps({'response': data}), code)
    response.headers.extend(headers or {})
    return response


def connect_db(test):
    if test:
        api.db = database.Database(True)
        api.token_timeout = 60
        api.exporter = export.Exporter(True)

    else:
        api.db = database.Database()
        api.token_timeout = int(os.environ.get("TOKEN_TIMEOUT"))
        api.exporter = export.Exporter(False)
        #api.notifier = Notifier()


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
                        "name": user["name"],
                        "email": user["email"],
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
        if check:
            return {"result": False}
        else:
            result = api.db.create_user(username, password, name, email, code)
            if result:
                result, user = api.db.check_password(username, password)
                return {
                    "result": result,
                    "user": {
                        "role": user["role"],
                        "username": user["username"],
                        "name": user["name"],
                        "email": user["email"],
                        "token": api.db.create_token(api.token_timeout, user["id"])
                    }
                }
            else:
                return {"result": False}


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
                return {"result": parse_json(slide)} if slide is not None else http.HTTPStatus.INTERNAL_SERVER_ERROR
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
                    return {"result": parse_json(result)}
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
        #email = request.args["email"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        if user["role"] != "admin":
            return http.HTTPStatus.FORBIDDEN()
        else:
            signup_code = api.db.create_signup_code(length, role)
            msg = f"You've been invited to slidedeck! Go to slidedeck-frontend.herokuapp.com/register and use code: {signup_code} to create an account!"
            #api.notifier.email(msg, "You've been invited to slidedeck", email)
            return signup_code


class AllUsers(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            return {"result": parse_json(api.db.get_all_users)}


class ChangePassword(Resource):
    def put(self):
        request_json = request.get_json()
        token = request_json["token"]
        user = api.db.check_token(token)
        new_password = request.args["new_password"]
        if user is None:
            abort(403, "bad token")
        else:
            return {"result": api.db.change_password(user, new_password)}


class DeleteUser(Resource):
    def delete(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        username = request.args["username"]
        if user is None:
            abort(403, "bad token")
        else:
            result = api.db.delete_user(username)
            return http.HTTPStatus.OK if result else http.HTTPStatus.BAD_REQUEST


class ExportLog(Resource):
    def get(self, log_id):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        else:
            api.exporter.export_log(api.db, log_id)
            return http.HTTPStatus.OK


class ExportLogDate(Resource):
    def put(self):
        request_json = request.get_json()
        token = request_json["token"]
        user = api.db.check_token(token)
        date = datetime.date(int(request_json["year"]), int(request_json["month"]), int(request_json["day"]))
        log_name = request_json["log_name"]
        if user is None:
            abort(403, "bad token")
        else:
            headers, slides, url = api.db.filter_slides_by_date_log(date, log_name, api.exporter)
            if headers is None or slides is None or url is None:
                print(headers, slides, url)
                abort(404, "not found")
            return {"result": {"headers": parse_json(headers), "slides":parse_json(slides), "url": url}}


class BackupLogs(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        url = api.exporter.export_all_logs(api.db)
        api.db.put_backup(url)
        return {"result": url}


class GetBackup(Resource):
    def get(self):
        token = request.args["token"]
        user = api.db.check_token(token)
        if user is None:
            abort(403, "bad token")
        url, date = api.db.get_backup
        if url is None:
            return {"result": None}
        return {"result": {"url": url, "date": date}}

api.add_resource(Login, "/login")
api.add_resource(Register, "/register")
api.add_resource(Token, "/token")
api.add_resource(SignupCode, "/signup")
api.add_resource(DeleteUser, "/users/delete/")
api.add_resource(AllUsers, "/users/")
api.add_resource(ChangePassword, "/password")

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
api.add_resource(ExportLogDate, "/log/export")
api.add_resource(BackupLogs, "/backup/create/")
api.add_resource(GetBackup, "/backup/current/")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        connect_db(True)
    else:
        connect_db(False)
    # context = ('server.crt', 'server.key')
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT")))  # , ssl_context=context)
else:
    connect_db(False)
