import asyncio
from playwright.async_api import async_playwright
from aiogram import Bot
from aiogram.types import FSInputFile
import os
from datetime import datetime
from app.config import config

async def generate_report_image(data: dict):
    """Генерирует PNG картинку из HTML с помощью Playwright."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    output_file = f"report_{datetime.now().strftime('%H%M%S')}.png"
    output_path = os.path.join('tmp', output_file)
    
    if not os.path.exists('tmp'):
        os.makedirs('tmp')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="uk">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                background-color: #f4f7f6;
                margin: 0; padding: 40px;
                display: flex; justify-content: center; align-items: flex-start;
                min-height: 100vh;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .report-card {{
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                width: 480px;
                border-top: 8px solid #2ecc71;
                box-sizing: border-box;
            }}
            .header {{ text-align: center; margin-bottom: 25px; border-bottom: 2px solid #f0f0f0; padding-bottom: 15px; }}
            .header h1 {{ margin: 0; font-size: 24px; color: #2c3e50; text-transform: uppercase; letter-spacing: 1px; }}
            .header .tc-name {{ margin: 10px 0 5px; color: #16a085; font-weight: bold; font-size: 18px; }}
            .header .date {{ color: #7f8c8d; font-size: 14px; }}
            
            .data-section {{ margin-top: 10px; }}
            .data-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 0;
                border-bottom: 1px solid #f9f9f9;
            }}
            .data-row:last-child {{ border-bottom: none; }}
            .label {{ font-weight: 600; color: #34495e; font-size: 15px; flex: 1; }}
            .value {{ color: #2c3e50; text-align: right; flex: 1; font-weight: 500; font-size: 16px; }}
            
            .status-ok {{ color: #27ae60; font-weight: bold; background: #e8f5e9; padding: 4px 12px; border-radius: 20px; }}
            .status-err {{ color: #e74c3c; font-weight: bold; background: #fdeaea; padding: 4px 12px; border-radius: 20px; }}
        </style>
    </head>
    <body>
        <div class="report-card">
            <div class="header">
                <h1>Звіт по ГПУ</h1>
                <div class="tc-name">{data.get('tc_name')}</div>
                <div class="date">Дата: {current_date}</div>
            </div>
            
            <div class="data-section">
                <div class="data-row">
                    <span class="label">1. Режим роботи:</span>
                    <span class="value">{data.get('work_mode')}</span>
                </div>
                
                <div class="data-row">
                    <span class="label">2. Час:</span>
                    <span class="value">{data.get('start_time')}</span>
                </div>
                
                <div class="data-row">
                    <span class="label">3. Потужність:</span>
                    <span class="value">{data.get('power_label')} - {data.get('load_power_percent')}% / {data.get('load_power_kw')} кВт</span>
                </div>
                
                <div class="data-row">
                    <span class="label">4. Статус роботи:</span>
                    <span class="value">
                        <span class="{ 'status-ok' if 'Стабільна' in data.get('gpu_status') else 'status-err' }">
                            {data.get('gpu_status')}
                        </span>
                    </span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        async with async_playwright() as p:
            # Запуск браузера (Chromium)
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Установка контента
            await page.set_content(html_content)
            
            # Ждем немного на всякий случай
            await asyncio.sleep(0.5)
            
            # Берем скриншот только карточки
            element = await page.query_selector(".report-card")
            if element:
                await element.screenshot(path=output_path)
                print(f"📸 Скріншот збережено: {output_path}")
            else:
                await page.screenshot(path=output_path)
                print(f"📸 Скріншот всього вікна (елемент не знайдено): {output_path}")
            
            await browser.close()
            return output_path
    except Exception as e:
        print(f"❌ Помилка Playwright: {e}")
        return None

async def main():
    test_data = {
        'tc_name': 'ТЦ Епіцентр К6 ГПУ-2 (KC GPU-2)',
        'work_mode': 'Мережа',
        'start_time': '07:00',
        'power_label': 'Поточна',
        'load_power_percent': '100',
        'load_power_kw': '1545.0',
        'gpu_status': 'Стабільна'
    }
    
    print("🚀 Генерація картинки через Playwright...")
    img = await generate_report_image(test_data)
    
    if img and os.path.exists(img):
        print(f"✅ Картинка готова: {img}")
        bot = Bot(token=config.bot_token.get_secret_value())
        try:
            photo = FSInputFile(img)
            await bot.send_photo(
                chat_id=config.test_special_group_id, 
                photo=photo, 
                caption="🖼️ Візуальний звіт (Playwright)"
            )
            print("🚀 Відправлено в Telegram!")
        except Exception as e:
            print(f"❌ Помилка відправки: {e}")
        finally:
            await bot.session.close()
    else:
        print("❌ Не вдалося створити візуальний звіт.")

if __name__ == "__main__":
    asyncio.run(main())
