export type UserRole = 'admin' | 'trader' | 'user';

export interface UserInfo {
  id: number;
  full_name: string;
  role: UserRole;
  username?: string;
}

export interface ObjectInfo {
  id: number;
  name: string;
  short_name?: string;
  work_mode?: string;
  gpu_status?: string;
  load_power_percent?: string;
  load_power_kw?: string;
  start_time?: string;
  time_type?: 'start' | 'stop';
  last_report_at?: string;
  reported_by?: string;
  telegram_group_id?: number;
  is_not_working?: boolean;
  current_schedule?: any[];
}

export interface ReportInfo {
  id: number;
  user_id: number;
  full_name: string;
  tc_name: string;
  work_mode: string;
  start_time: string;
  load_power_percent?: string;
  load_power_kw?: string;
  gpu_status: string;
  battery_voltage?: string;
  pressure_before?: number;
  pressure_after?: string;
  total_mwh?: number;
  total_hours?: number;
  oil_sampling_limit?: number;
  created_at: string;
}

export interface SummaryReportData {
  id: number;
  tc_name: string;
  work_mode: string;
  start_time: string;
  load_power_percent: string;
  load_power_kw: string;
  gpu_status: string;
  total_mwh: number;
  total_hours: number;
  duty_info: string;
  created_at_kiev: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  full_name: string;
}
