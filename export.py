import datetime

import openpyxl
import database


def export_log(database, log_id):
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
def export_log_date(database, log_id, date):
    log = database.get_log(log_id)
    template = database.get_template(log["template"])
    template_headers = template["headers"].keys()
    slides = database.get_slides(log_id)
    filtered_slides = [slide for slide in slides if datetime.date.fromisoformat(slide["created"]) - date == 0]
    filtered_slides = [slide for slide in filtered_slides if slide["submitted"]]
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = log["name"]
    for i, key in enumerate(template_headers):
        worksheet.cell(1, i+1, key)
    for i, slide in enumerate(filtered_slides):
        for j, key in enumerate(template_headers):
            worksheet.cell(2+i, j+1, slide["fields"][key])
    workbook.save(f"{log['name']}.xlsx")
    return "url"
