import datetime
import os

import openpyxl
from botocore.exceptions import ClientError

import database
import boto3
from botocore.config import Config


class Exporter:
    def __init__(self, test):
        boto_config = Config(
            region_name='us-east-1',
            signature_version='v4',
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            }
        )
        self.test = test
        if not test:
            self.client = boto3.client('s3', config=boto_config)
            self.bucket = os.getenv("EXPORT_BUCKET")

    def export_log(self, database, log_id):
        log = database.get_log(log_id)
        template = database.get_template(log["template"])
        template_headers = template["headers"].keys()
        slides = database.get_slides(log_id)
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = log["name"]
        for i, key in enumerate(template_headers):
            worksheet.cell(1, i+1, key)
        for i, slide in enumerate(slides):
            for j, key in enumerate(template_headers):
                worksheet.cell(2+i, j+1, slide["fields"][key])
        workbook.save(f"{log['name']}.xlsx")

    def export_log_date(self, database, log_id, date):
        log = database.get_log(log_id)
        template = database.get_template(log["template"])
        template_headers = template["headers"].keys()
        slides = database.get_slides(log_id)
        filtered_slides = [slide for slide in slides if datetime.date.fromisoformat(slide["created"][:10]) - date == 0]
        filtered_slides = [slide for slide in filtered_slides if slide["submitted"]]
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = log["name"]
        for i, key in enumerate(template_headers):
            worksheet.cell(1, i+1, key)
        for i, slide in enumerate(filtered_slides):
            for j, key in enumerate(template_headers):
                worksheet.cell(2+i, j+1, slide["fields"][key])
        file_name = f"{log['name']-date.isoformat()}"
        workbook.save(file_name+".xlsx")
        if not self.test:
            try:
                response = self.client.upload_file(file_name+".xlsx", self.bucket, file_name)
                os.remove(file_name+".xlsx")
            except ClientError as e:
                return None
            return f"https://slide-export.s3.amazonaws.com/{file_name}"
        else:
            return "url"
