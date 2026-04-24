from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime

class AuthRequest(BaseModel):
    identifier: str # Phone or !TG_ID

class AuthVerify(BaseModel):
    identifier: str
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str

class UserInfo(BaseModel):
    id: int
    full_name: str
    role: str
    username: Optional[str] = None

class ObjectInfo(BaseModel):
    id: int
    name: str
    short_name: Optional[str] = None
    work_mode: Optional[str] = None
    gpu_status: Optional[str] = None
    load_power_percent: Optional[str] = None
    load_power_kw: Optional[str] = None
    start_time: Optional[str] = None
    time_type: Optional[str] = None # 'start', 'stop' or None
    last_report_at: Optional[datetime] = None
    reported_by: Optional[str] = None
    telegram_group_id: Optional[int] = None
    is_not_working: bool = False
    current_schedule: List[Any] = []

class ReportInfo(BaseModel):
    id: int
    user_id: int
    full_name: str
    tc_name: str
    work_mode: str
    start_time: str
    load_power_percent: Optional[str] = None
    load_power_kw: Optional[str] = None
    gpu_status: str
    battery_voltage: Optional[str] = None
    pressure_before: Optional[float] = None
    pressure_after: Optional[str] = None
    total_mwh: Optional[float] = None
    total_hours: Optional[float] = None
    oil_sampling_limit: Optional[float] = None
    created_at: datetime

class ScheduleInterval(BaseModel):
    start: str
    end: str
    power: int
    mode: str

class TraderObjectSchedule(BaseModel):
    db_name: str
    target_date: str
    intervals: List[ScheduleInterval]
    is_not_working: bool

class TraderPublishRequest(BaseModel):
    date_str: str # Format: DD/MM/YYYY or YYYY-MM-DD
    items: List[TraderObjectSchedule]

class ExportRequest(BaseModel):
    start_date: str # YYYY-MM-DD
    end_date: str # YYYY-MM-DD
