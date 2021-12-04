import http
import os
import hashlib
import hmac
import datetime
import uuid


from pymongo import MongoClient


class Database:
    def __init__(self, test=False):
        if test:
            client = MongoClient("localhost")
            self.db = client.test
            self.db.templates.drop()
            self.db.users.drop()
            self.db.tests.drop()
            self.db.logs.drop()
            self.db.tokens.drop()
            self.db.slides.drop()
        else:
            # client = MongoClient(os.environ.get("MONGODB_IP"),
            #                      username=os.environ.get("MONGODB_USERNAME"),
            #                      password=os.environ.get("MONGODB_PASSWORD"),
            #                      authSource=os.environ.get("MONGODB_DBNAME"),
            #                      authMechanism="SCRAM-SHA-1")
            username = os.environ.get("MONGODB_USERNAME")
            password = os.environ.get("MONGODB_PASSWORD")
            ip = os.environ.get("MONGODB_IP")
            db_name = os.environ.get("MONGODB_DBNAME")
            url = f"mongodb+srv://{username}:{password}@{ip}/{db_name}?retryWrites=true&w=majority"
            client = MongoClient(url)
            self.db = client.get_database("SlideDeck")
            print(self.create_signup_code(3, "admin"))

    def check_user_exists(self, name):
        count = self.db.users.count_documents({"username": name})
        if count > 0:
            return True
        else:
            return False

    def create_user(self, username, password, name, email, code):
        role = self.check_signup_code(code)
        if role is None:
            return False
        else:
            try:
                salt = os.urandom(16)
                password_hash = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, 100000)
                self.db.users.insert_one({
                    "username": username,
                    "hash": password_hash,
                    "salt": salt,
                    "id": uuid.uuid4().hex,
                    "name": name,
                    "email": email,
                    "role": role
                })
                return True
            except Exception as e:
                print(e)
                return False

    def get_all_users(self):
        users = []
        for user in self.db.users.find():
            users.append({"user": {
                          "role": user["role"],
                          "username": user["username"],
                          "name": user["name"],
                          "email": user["email"],
                           }})
        return users

    def delete_user(self, username):
        if self.check_user_exists():
            self.db.users.delete_one({"username": username})
            return True
        else:
            return False

    def check_password(self, name, password):
        user = self.db.users.find_one({"username": name})
        if not user:
            return False, None
        result = hmac.compare_digest(
            user["hash"],
            hashlib.pbkdf2_hmac("sha512", password.encode(), user["salt"], 100000)
        )
        return result, user if result else None

    def create_token(self, expiration_length, user_id):
        token = os.urandom(16)
        self.db.tokens.insert_one(
            {
                "token": token,
                "timeout": expiration_length,
                "last_used": datetime.datetime.now(),
                "user": user_id
            }
        )
        return token.hex()

    def check_token(self, token):
        try:
            token_obj = self.db.tokens.find_one({"token": bytes.fromhex(token)})
        except ValueError:
            return None
        if token_obj is None:
            return None
        elif datetime.datetime.now() - token_obj["last_used"] < datetime.timedelta(seconds=token_obj["timeout"]):
            self.db.tokens.update_one(
                {"token": bytes.fromhex(token)},
                {"$set": {"last_used": datetime.datetime.now()}}
            )
            return self.db.users.find_one({"id": token_obj["user"]})
        else:
            self.db.tokens.delete_one({"token": token})
            return None

    def create_signup_code(self, expiration_length, role):
        code = os.urandom(4)
        self.db.codes.insert_one(
            {
                "code": code,
                "timeout": expiration_length,
                "created": datetime.datetime.now(),
                "role": role
            }
        )
        return code.hex()

    def check_signup_code(self, code):
        try:
            code_object = self.db.codes.find_one({"code": bytes.fromhex(code)})
        except ValueError:
            return None
        if code_object is None:
            return None
        elif datetime.datetime.now() - code_object["created"] < datetime.timedelta(hours=code_object["timeout"]):
            role = code_object["role"]
            self.db.codes.delete_one({"code": code})
            return role
        else:
            self.db.codes.delete_one({"code": code})
            return None

    def create_template(self, name, columns):
        template = {"name": name, "headers": {}}
        now = datetime.datetime.now().isoformat()
        template["created"] = now
        template["touched"] = now
        template["id"] = uuid.uuid4().hex
        for column in columns:
            template["headers"][column["title"]] = [column["type"], column["role"]]
        try:
            self.db.templates.insert_one(template)
            template["headers"] = [*zip(template["headers"].keys(), template["headers"].values())]
            return template
        except:
            return http.HTTPStatus.INTERNAL_SERVER_ERROR

    def get_templates(self):
        templates = []
        for template in self.db.templates.find():
            template["headers"] = [*zip(template["headers"].keys(), template["headers"].values())]
            templates.append(template)
        return templates

    def get_template(self, template_id):
        template = self.db.templates.find_one({"id": template_id})
        if template:
            template["headers"] = [*zip(template["headers"].keys(), template["headers"].values())]
        return template

    def filter_slides_by_date_log(self, date, log, exporter):
        log = self.db.logs.find_one({"name": log})
        if not log:
            return None, None, None
        template = self.get_template(log["template"])
        slides = self.get_slides(log["id"])
        filtered_slides = [slide for slide in slides if datetime.date.fromisoformat(slide["created"]) - date == 0]
        url = exporter.export_log_date(self.db, log["id"], date)
        return template["headers"], filtered_slides, url



    def create_test(self, name, template_id, fields):
        test = {
            "name": name,
            "template": template_id,
            "fields": fields,
        }
        now = datetime.datetime.now().isoformat()
        test["created"] = now
        test["touched"] = now
        test["id"] = uuid.uuid4().hex
        try:
            self.db.tests.insert_one(test)
            return True
        except:
            return False

    def get_tests(self):
        tests = []
        for test in self.db.tests.find():
            tests.append(test)
        return tests

    def create_log(self, template_id, presets, name):
        try:
            template = self.db.templates.find_one({"id": template_id})
            if template:
                log = {"id": uuid.uuid4().hex, "slides": [], "template": template_id}
            else:
                return http.HTTPStatus.BAD_REQUEST
        except Exception as e:
            print(e)
            return http.HTTPStatus.BAD_REQUEST
        log["name"] = name
        log["presets"] = presets
        now = datetime.datetime.now().isoformat()
        log["created"] = now
        log["touched"] = now
        self.db.logs.insert_one(log)
        return log

    def get_logs(self):
        logs = []
        for log in self.db.logs.find():
            logs.append(log)
        return logs

    def get_log(self, log_id):
        result = self.db.logs.find_one({"id": log_id})
        if result is None:
            return http.HTTPStatus.BAD_REQUEST
        else:
            return result

    def post_slide(self, log_id, fields, submit, user):
        log = self.db.logs.find_one({"id": log_id})
        if log is None:
            return None
        else:
            slide = {"id": uuid.uuid4().hex,
                     "log": log_id,
                     "submitted": submit,
                     "reviewed": {"date": None, "status": False}
                     }
            try:
                headers = self.db.templates.find_one({"id": log["template"]})["headers"]
                valid_fields = {}
                for key in fields.keys():
                    if headers[key][1] == user["role"]:
                        valid_fields[key] = fields[key]
                    else:
                        valid_fields[key] = None
                slide["fields"] = valid_fields
                now = datetime.datetime.now().isoformat()
                slide["created"] = now
                slide["touched"] = now
                slide["users"] = [user["id"]]
            except Exception as e:
                print(e)
                return None
            log_slides = log["slides"]
            log_slides.append(slide["id"])
            self.db.logs.update_one({"id": log_id}, {"$set": {"slides": log_slides}})
            self.db.slides.insert_one(slide)
            slide["fields"] = [*zip(slide["fields"].keys(), slide["fields"].values())]
            return slide

    def edit_slide(self, slide_id, fields, submit, user):
        slide = self.db.slides.find_one({"id": slide_id})
        if slide is None:
            return http.HTTPStatus.BAD_REQUEST
        else:
            if not slide["submitted"] and submit:
                self.db.slides.update_one({"id": slide_id}, {"$set": {"submitted": submit}})
            try:
                log = self.db.logs.find_one({"id": slide["log"]})
                headers = self.db.templates.find_one({"id": log["template"]})["headers"]
                valid_fields = slide["fields"]
                for key in fields.keys():
                    if headers[key][1] == user["role"]:
                        valid_fields[key] = fields[key]
                self.db.slides.update_one({"id": slide_id}, {"$set": {"fields": valid_fields}})
                return True
            except:
                return False

    def get_slide(self, slide_id):
        slide = self.db.slides.find_one({"id": slide_id})
        if slide is None:
            return http.HTTPStatus.BAD_REQUEST
        else:
            slide["fields"] = [*zip(slide["fields"].keys(), slide["fields"].values())]
            return slide

    def get_slides(self, log_id):
        log = self.db.logs.find_one({"id": log_id})
        slide_ids = log["slides"]
        slides = []
        for slide_id in slide_ids:
            slide = self.db.slides.find_one({"id": slide_id})
            if slide:
                slide["fields"] = [*zip(slide["fields"].keys(), slide["fields"].values())]
                slides.append(slide)
        return slides

    def delete_template(self, template_id):
        log_count = self.db.logs.count_documents({"template": template_id})
        if log_count == 0:
            self.db.templates.delete_one({"id": template_id})
            return True
        else:
            return False