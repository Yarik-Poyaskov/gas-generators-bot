import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional

from app.db.database import get_schedule_by_object_and_date, get_latest_report_for_object

logger = logging.getLogger(__name__)

def time_to_mins(t_str: Any) -> Optional[int]:
    """Converts 'HH:MM' string to minutes from midnight."""
    if not t_str:
        return None
    try:
        clean = re.search(r'(\d{1,2}):(\d{2})', str(t_str).strip())
        if clean:
            return int(clean.group(1)) * 60 + int(clean.group(2))
    except Exception:
        pass
    return None

async def classify_report_status(data: Dict[str, Any], exclude_report_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifies a report into one of the 8 status categories:
    🟢 Зелене коло: плановий старт згідно графіка трейдера
    🟡 Жовте коло: старт із запізненням > 5 хв або поза графіком (ручний режим)
    🟠 Помаранчове коло: старт вчасно, але не співпадає режим (мережа/острів)
    🟣 Фіолетове коло: старт ГПУ після аварійної зупинки
    🔴 Червоне коло: запуск вчасно і планово, але з технічними аваріями
    
    🟩 Зелений квадрат: планова зупинка
    🟨 Жовтий квадрат: ГПУ допрацювала по графіку і зупинилась з несправностями (подальший пуск можливий)
    🟥 Червоний квадрат: аварійна зупинка (експлуатація неможлива)
    
    ⚠️ Жовтий трикутник: попередження під час роботи/огляду без зупинки
    
    Returns a dict with:
      - marker: emoji symbol
      - code: string code
      - title: short title
      - display_status: text for point 4 in report
      - send_to_special: bool (send to SPECIAL_GROUP_ID?)
      - send_to_attention: bool (send to ATTENTION_GROUP_ID?)
      - reason: debug explanation
    """
    obj_id = data.get("obj_id")
    time_label = (data.get("time_label") or "").lower()
    work_mode = data.get("work_mode") or ""
    gpu_status = data.get("gpu_status") or ""
    start_time_str = data.get("start_time") or ""
    is_short = data.get("is_short", False)

    # 1. Determine if this is a START, STOP, or WORK/ROUTINE event
    is_start = False
    is_stop = False

    if "запуск" in time_label:
        is_start = True
    elif "зупинк" in time_label or "не працює" in gpu_status.lower() or "не працює" in work_mode.lower() or "не готова" in work_mode.lower():
        is_stop = True
    else:
        # If no explicit label:
        if "не готова" in work_mode.lower() or "не працює" in work_mode.lower():
            is_stop = True
        elif is_short and work_mode in ["Острів", "Мережа"]:
            is_start = True

    # Get previous report and today's trader schedule
    previous_report = None
    today_schedule = None
    if obj_id:
        try:
            previous_report = await get_latest_report_for_object(obj_id, exclude_report_id=exclude_report_id)
        except Exception as e:
            logger.error(f"Error fetching previous report for obj {obj_id}: {e}")

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_schedule = await get_schedule_by_object_and_date(obj_id, today_str)
        except Exception as e:
            logger.error(f"Error fetching today schedule for obj {obj_id}: {e}")

    # Check if previous state was an accident
    prev_was_accident = False
    if previous_report:
        prev_wm = (previous_report.get("work_mode") or "").lower()
        prev_gs = (previous_report.get("gpu_status") or "").lower()
        if "аварі" in prev_wm or "не готова" in prev_wm or "аварі" in prev_gs:
            prev_was_accident = True

    # Parse schedule intervals
    intervals = []
    if today_schedule and today_schedule.get("schedule_json") and not today_schedule.get("is_not_working"):
        try:
            parsed = json.loads(today_schedule["schedule_json"])
            for inv in parsed:
                if isinstance(inv, dict) and inv.get("start") and inv.get("end"):
                    intervals.append(inv)
        except Exception as e:
            logger.error(f"Error parsing schedule_json: {e}")

    # -------------------------------------------------------------
    # A. LOGIC FOR START (КОЛА)
    # -------------------------------------------------------------
    if is_start:
        # Rule 1: 🟣 Фіолетове коло - старт після аварійного простою
        if prev_was_accident:
            return {
                "marker": "🟣",
                "code": "purple_circle",
                "title": "Старт ГПУ після аварійної зупинки",
                "display_status": "🟣 Старт ГПУ після аварійної зупинки",
                "send_to_special": True,     # Трейдерам потрібно!
                "send_to_attention": True,   # В "Увага" потрібно!
                "reason": "Previous report was in accident state"
            }

        # Check schedule
        if not intervals:
            # Немає графіка на сьогодні -> 🟡 Жовте коло (неплановий старт / ручний режим)
            return {
                "marker": "🟡",
                "code": "yellow_circle",
                "title": "Неплановий старт (ручний режим)",
                "display_status": "🟡 Неплановий старт (без графіка / ручний режим)",
                "send_to_special": True,     # Трейдерам потрібно!
                "send_to_attention": True,   # В "Увага" потрібно!
                "reason": "No trader schedule found for today"
            }

        start_mins = time_to_mins(start_time_str)
        if start_mins is None:
            return {
                "marker": "🟡",
                "code": "yellow_circle",
                "title": "Неплановий старт",
                "display_status": f"🟡 Неплановий старт ({start_time_str})",
                "send_to_special": True,
                "send_to_attention": True,
                "reason": "No parseable start time"
            }

        # Find closest interval by start time
        best_inv = None
        min_diff = 9999
        for inv in intervals:
            inv_start = time_to_mins(inv.get("start"))
            if inv_start is not None:
                diff = abs(start_mins - inv_start)
                if diff < min_diff:
                    min_diff = diff
                    best_inv = inv

        if not best_inv or min_diff > 120:
            # Started more than 2 hours away from any scheduled interval
            return {
                "marker": "🟡",
                "code": "yellow_circle",
                "title": "Неплановий старт (поза графіком)",
                "display_status": f"🟡 Неплановий старт (поза графіком трейдера, час: {start_time_str})",
                "send_to_special": True,
                "send_to_attention": True,
                "reason": f"Start time {start_time_str} is outside schedule intervals"
            }

        planned_start_mins = time_to_mins(best_inv.get("start"))
        delay_mins = start_mins - planned_start_mins

        # Rule 2: 🟡 Жовте коло - запізнення > 5 хвилин
        if delay_mins > 5:
            return {
                "marker": "🟡",
                "code": "yellow_circle",
                "title": f"Запуск із запізненням > 5 хв (+{delay_mins} хв)",
                "display_status": f"🟡 Запуск із запізненням (+{delay_mins} хв, план {best_inv.get('start')}, факт {start_time_str})",
                "send_to_special": True,
                "send_to_attention": True,
                "reason": f"Start delay of {delay_mins} mins (> 5 mins)"
            }

        # Rule 3: 🟠 Помаранчове коло - не співпадає режим (мережа / острів)
        planned_mode = best_inv.get("mode") or ""
        clean_actual_mode = "мереж" if "мереж" in work_mode.lower() else ("острів" if "остр" in work_mode.lower() else work_mode.lower())
        clean_planned_mode = "мереж" if "мереж" in planned_mode.lower() else ("острів" if "остр" in planned_mode.lower() else planned_mode.lower())

        if clean_planned_mode and clean_actual_mode != clean_planned_mode:
            return {
                "marker": "🟠",
                "code": "orange_circle",
                "title": f"Не співпадає режим роботи ({work_mode} замість {planned_mode})",
                "display_status": f"🟠 Не співпадає режим роботи (план: {planned_mode}, факт: {work_mode})",
                "send_to_special": True,
                "send_to_attention": True,
                "reason": f"Mode mismatch: planned {planned_mode} vs actual {work_mode}"
            }

        # Rule 4 & 5: Check technical accident
        has_accident = "аварі" in gpu_status.lower()
        if has_accident:
            # 🔴 Червоне коло - вчасно, але з технічними аваріями
            return {
                "marker": "🔴",
                "code": "red_circle",
                "title": "Запуск вчасно (з технічними аваріями)",
                "display_status": "🔴 Запуск вчасно і планово, але з технічними аваріями",
                "send_to_special": True,     # Трейдерам відправляємо
                "send_to_attention": False,
                "reason": "Started on time, mode match, but technical accident reported"
            }

        # 🟢 Зелене коло - ідеальний плановий пуск
        return {
            "marker": "🟢",
            "code": "green_circle",
            "title": "Плановий старт",
            "display_status": "🟢 Плановий старт (згідно графіка)",
            "send_to_special": True,         # Трейдерам відправляємо
            "send_to_attention": False,
            "reason": "Planned start on time, mode matches, stable"
        }

    # -------------------------------------------------------------
    # B. LOGIC FOR STOP (КВАДРАТИ)
    # -------------------------------------------------------------
    if is_stop:
        has_accident = "аварі" in gpu_status.lower()
        is_hard_accident_mode = ("не готова" in work_mode.lower() or "аварії" in work_mode.lower())

        # Check if stop matches end of schedule
        stopped_at_end_of_schedule = False
        stop_mins = time_to_mins(start_time_str)
        if stop_mins is not None and intervals:
            for inv in intervals:
                end_mins = time_to_mins(inv.get("end"))
                if end_mins is not None and abs(stop_mins - end_mins) <= 25:
                    stopped_at_end_of_schedule = True
                    break

        # Rule: 🟥 Червоний квадрат - аварійна зупинка, подальша експлуатація неможлива
        if is_hard_accident_mode or (has_accident and not stopped_at_end_of_schedule):
            return {
                "marker": "🟥",
                "code": "red_square",
                "title": "Аварійна зупинка",
                "display_status": "🟥 Аварійна зупинка (подальша експлуатація неможлива)",
                "send_to_special": True,     # Трейдерам потрібно!
                "send_to_attention": True,   # В "Увага" обов'язково!
                "reason": "Accident stop / hard accident mode"
            }

        # Rule: 🟨 Жовтий квадрат - допрацювала по графіку, але зупинилась з несправностями
        if has_accident:
            return {
                "marker": "🟨",
                "code": "yellow_square",
                "title": "Зупинка з несправностями",
                "display_status": "🟨 Зупинка з несправностями (подальший пуск можливий)",
                "send_to_special": True,
                "send_to_attention": False,
                "reason": "Completed schedule but stopped with defects"
            }

        # Rule: 🟩 Зелений квадрат - планова зупинка
        return {
            "marker": "🟩",
            "code": "green_square",
            "title": "Планова зупинка",
            "display_status": "🟩 Планова зупинка",
            "send_to_special": True,
            "send_to_attention": False,
            "reason": "Normal planned stop"
        }

    # -------------------------------------------------------------
    # C. LOGIC FOR WORK / ROUTINE CHECKLIST (БЕЗ ЗУПИНКИ)
    # -------------------------------------------------------------
    has_accident = "аварі" in gpu_status.lower()
    if has_accident:
        return {
            "marker": "⚠️",
            "code": "warning_triangle",
            "title": "Попередження (несправність під час роботи)",
            "display_status": "⚠️ Попередження (несправність без зупинки)",
            "send_to_special": False,
            "send_to_attention": False,
            "reason": "Working with technical defects without stop"
        }

    return {
        "marker": "🟢",
        "code": "normal_work",
        "title": "Статус ГПУ",
        "display_status": gpu_status or "Стабільна",
        "send_to_special": False,
        "send_to_attention": False,
        "reason": "Normal ongoing operation"
    }

