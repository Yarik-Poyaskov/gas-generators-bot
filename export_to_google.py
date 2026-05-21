import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import io
import re
import json
import requests
import google.auth.transport.requests
from app.config import config

# Настройки теперь берутся из .env через config
DB_PATH = "reports.db"
JSON_KEY_FILE = config.google_sheets_json_key
SPREADSHEET_URL = config.google_sheets_url

def export_to_google(report_data: dict):
    """Appends a single report row to Google Sheets."""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        credentials = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scope)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(SPREADSHEET_URL)
        worksheet = sh.get_worksheet(0)
        
        # 1. Очищаем время запуска от лишнего текста
        start_time = report_data.get('start_time', '')
        if isinstance(start_time, str) and "Плановий - " in start_time:
            start_time = start_time.replace("Плановий - ", "")
        
        # 2. Получаем текущую дату и время ОТДЕЛЬНО
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d") # Формат: 2026-03-03
        time_str_report = now.strftime("%H:%M:%S") # Время подачи
        
        # 3. Подготовка строки данных (Дата и Время теперь разделены)
        row = [
            date_str,                      # Дата
            time_str_report,               # Время подачи
            report_data.get('tc_name'),
            report_data.get('full_name'),
            report_data.get('work_mode'),
            start_time,                    # Очищенное время запуска
            report_data.get('load_power_percent'),
            report_data.get('load_power_kw'),
            report_data.get('gpu_status'),
            report_data.get('battery_voltage'),
            report_data.get('pressure_before'),
            report_data.get('pressure_after'),
            report_data.get('total_mwh'),
            report_data.get('total_hours'),
            report_data.get('oil_sampling_limit')
        ]
        
        # value_input_option='USER_ENTERED' заставляет Google Sheets парсить строки как даты/числа
        worksheet.append_row(row, value_input_option='USER_ENTERED')
        print(f"Отчет успешно добавлен в Google Таблицу (объект: {report_data.get('tc_name')})")
        
    except Exception as e:
        print(f"Ошибка экспорта в Google: {e}")

import base64

def upload_photo_to_google_drive(file_name: str, file_bytes: bytes, survey_title: str = None) -> dict:
    """
    Uploads a photo to Google Drive by sending a request to the Google Apps Script Web App.
    Returns a dict with 'view_url' and 'download_url'.
    """
    script_url = getattr(config, 'google_apps_script_url', None)
    script_token = getattr(config, 'google_apps_script_token', None)
    
    if not script_url:
        raise Exception("GOOGLE_APPS_SCRIPT_URL is not configured in .env")
        
    # Encode bytes to base64 string
    base64_data = base64.b64encode(file_bytes).decode('utf-8')
    
    payload = {
        "token": script_token,
        "fileName": file_name,
        "fileData": base64_data,
        "surveyTitle": survey_title
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # We must follow redirects because Google Apps Script Web App URLs redirect (HTTP 302) to googleusercontent.com
    r = requests.post(script_url, json=payload, headers=headers, allow_redirects=True)
    
    if r.status_code != 200:
        raise Exception(f"Google Apps Script returned status code {r.status_code}: {r.text}")
        
    try:
        res = r.json()
    except Exception as e:
        raise Exception(f"Failed to parse JSON response from Google Apps Script: {r.text}")
        
    if res.get("status") == "error":
        raise Exception(f"Google Apps Script error: {res.get('message')}")
        
    return {
        "view_url": res["viewUrl"],
        "download_url": res["downloadUrl"]
    }

def export_survey_to_google(survey_title: str, response_data: dict, photo_urls: list = None):
    """
    Exports a single survey response to Google Sheets.
    Creates a new worksheet with survey_title if it doesn't exist.
    """
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        credentials = Credentials.from_service_account_file(JSON_KEY_FILE, scopes=scope)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_url(SPREADSHEET_URL)
        
        # 1. Find or create sheet
        worksheet = None
        try:
            worksheet = sh.worksheet(survey_title)
        except gspread.WorksheetNotFound:
            # Create sheet
            worksheet = sh.add_worksheet(title=survey_title, rows=1000, cols=10)
            headers = ["Дата та час відповіді", "Об'єкт", "Користувач", "Відповідь", "Коментар"]
            for i in range(1, 6):
                headers.append(f"Фото {i}")
            worksheet.append_row(headers)
            # Format header row (bold)
            worksheet.format("A1:J1", {"textFormat": {"bold": True}})
            
        # 2. Prepare data row
        now = datetime.now()
        datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            datetime_str,
            response_data.get('tc_name'),
            response_data.get('full_name'),
            response_data.get('answer'),
            response_data.get('comment') or ''
        ]
        
        # Add photo formulas (up to 5)
        if photo_urls:
            for url_info in photo_urls[:5]:
                # Formulas in gspread must use semicolon as arguments separator for UA/RU locales
                formula = f'=HYPERLINK("{url_info["view_url"]}"; IMAGE("{url_info["download_url"]}"))'
                row.append(formula)
                
        worksheet.append_row(row, value_input_option='USER_ENTERED')
        print(f"Survey response for '{survey_title}' exported to Google Sheets")
        
    except Exception as e:
        print(f"Error exporting survey to Google Sheets: {e}")

async def export_survey_response_task(bot, survey_id: int, full_name: str, tc_name: str, answer: str, photos: list, comment: str):
    """Asynchronous background task to process and export survey response."""
    try:
        from app.db.database import get_survey
        survey = await get_survey(survey_id)
        title = survey.get('title') if (survey and survey.get('title')) else "Без теми"
        
        photo_urls = []
        if photos:
            for idx, photo_id in enumerate(photos, start=1):
                try:
                    file_info = await bot.get_file(photo_id)
                    photo_bytes = io.BytesIO()
                    await bot.download_file(file_info.file_path, photo_bytes)
                    file_data = photo_bytes.getvalue()
                    
                    # Clean file names
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                    safe_obj = re.sub(r'[\\/*?:"<>|]', "", tc_name)
                    file_name = f"{safe_title}_{safe_obj}_{idx}.jpg"
                    
                    # Upload to Google Drive (run blocking requests call in executor)
                    import asyncio
                    loop = asyncio.get_event_loop()
                    urls = await loop.run_in_executor(None, upload_photo_to_google_drive, file_name, file_data, title)
                    photo_urls.append(urls)
                except Exception as ex:
                    print(f"Error processing photo {photo_id} in task: {ex}")
                    
        # Export to Google Sheets
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, export_survey_to_google, title, {
            'tc_name': tc_name,
            'full_name': full_name,
            'answer': answer,
            'comment': comment
        }, photo_urls)
        
    except Exception as e:
        print(f"Error in export_survey_response_task: {e}")

if __name__ == "__main__":
    pass
