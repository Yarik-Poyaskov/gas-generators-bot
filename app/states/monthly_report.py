from aiogram.fsm.state import State, StatesGroup

class MonthlyReportState(StatesGroup):
    selecting_object = State()
    energy_mwh = State()
    gas_corrector_total = State() # For reports directly from corrector
    gas_start = State()
    gas_end = State()
    gas_coef = State()
    oil_start = State()
    oil_added = State()
    oil_end = State()
    waiting_for_confirmation = State()
