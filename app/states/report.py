from aiogram.fsm.state import State, StatesGroup

class ReportState(StatesGroup):
    selecting_object = State()   # Выбор объекта для отчета
    is_short = State()           # Флаг: скорочений чи повний звіт
    is_gpu_working = State()     # Чи працює зараз ГПУ? (Yes/No)
    work_mode = State()
    is_launch_planned = State()
    planned_work_mode = State()
    time_type = State()          # "Час пуску" або "Час зупинки"
    start_time = State()
    power_type = State()         # "Поточна" або "Планова"
    load_power_percent = State() # Новое состояние для Потужність (%)
    load_power_kw = State()      # Новое состояние для Потужність (кВт)
    gpu_status = State()
    battery_voltage = State()
    pressure_before = State()
    pressure_after = State()
    total_mwh = State()
    total_hours = State()
    oil_sampling_limit = State()
    apparatus_check = State()
    photo_multimeter = State()
    photo_shos = State()
    waiting_for_confirmation = State()
