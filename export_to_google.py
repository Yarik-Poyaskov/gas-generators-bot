import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
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

if __name__ == "__main__":
    pass
