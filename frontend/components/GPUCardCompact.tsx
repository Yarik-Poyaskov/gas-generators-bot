'use client';

import { ObjectInfo } from '@/types';
import { 
  Zap, 
  Activity, 
  Clock, 
  User, 
  Settings2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Calendar,
  ChevronDown,
  ChevronUp,
  FileText,
  Phone
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

interface GPUCardProps {
  data: ObjectInfo;
  isNew?: boolean;
}

export default function GPUCardCompact({ data, isNew }: GPUCardProps) {
  const [openSection, setOpenSection] = useState<'none' | 'schedule' | 'last_report' | 'shift'>('none');

  const toggleSection = (section: 'schedule' | 'last_report' | 'shift') => {
    setOpenSection(openSection === section ? 'none' : section);
  };

  const getStatusColor = () => {
    const status = (data.gpu_status || '').toLowerCase();
    if (status.includes('аварії') || status.includes('не готова') || status.includes('аваріями')) return 'orange';
    if (status.includes('стабільна')) return 'green';
    if (status.includes('не працює')) return 'red';
    return 'blue';
  };

  const statusColor = getStatusColor();
  const theme = {
    green: { bg: 'bg-emerald-50 dark:bg-emerald-950/20', border: 'border-emerald-100', text: 'text-emerald-600', accent: 'bg-emerald-500/10' },
    red: { bg: 'bg-rose-50 dark:bg-rose-950/20', border: 'border-rose-100', text: 'text-rose-600', accent: 'bg-rose-500/10' },
    orange: { bg: 'bg-amber-50 dark:bg-amber-950/20', border: 'border-amber-100', text: 'text-amber-600', accent: 'bg-amber-500/10' },
    blue: { bg: 'bg-blue-50 dark:bg-blue-950/20', border: 'border-blue-100', text: 'text-blue-600', accent: 'bg-[#004899]/10' },
  }[statusColor];

  const Icon = statusColor === 'green' ? CheckCircle2 : statusColor === 'red' ? XCircle : statusColor === 'orange' ? AlertTriangle : Activity;
  const glowHex = { green: '#10b981', red: '#f43f5e', orange: '#f59e0b', blue: '#004899' }[statusColor];
  const glowRgba = { green: '16, 185, 129', red: '244, 63, 94', orange: '245, 158, 11', blue: '0, 72, 153' }[statusColor];

  const mainMode = (data.work_mode === 'Мережа' || data.work_mode === 'Острів') ? data.work_mode : '—';
  const detailStatus = data.gpu_status ? data.gpu_status.split(',')[0] : 'Очікування';

  // --- Date/Report Logic ---
  const now = new Date();
  const rawReportDate = data.last_report_at;
  let reportDate: Date | null = null;
  if (rawReportDate) {
    const isoDate = typeof rawReportDate === 'string' 
      ? (rawReportDate.includes('T') ? rawReportDate : rawReportDate.replace(' ', 'T') + 'Z')
      : rawReportDate.toISOString();
    reportDate = new Date(isoDate);
  }
  const isReportToday = reportDate && reportDate.getUTCDate() === now.getUTCDate() && reportDate.getUTCMonth() === now.getUTCMonth();

  const getPlannedTime = () => {
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    const status = (data.gpu_status || '').toLowerCase();
    const isRunning = isReportToday && (status.includes('стабільна') || status.includes('аваріями'));
    const lastReportTime = (isReportToday && data.start_time) ? data.start_time : null;

    if (data.is_not_working) return { label: 'Запуск', value: 'не планується' };
    
    if (!data.current_schedule || data.current_schedule.length === 0) {
      if (!isRunning) return { label: 'Запуск', value: 'не планується' };
      return { label: data.time_type === 'start' ? 'Час запуску' : 'Час зупинки', value: lastReportTime || '—' };
    }

    const intervals = data.current_schedule.map((item: any) => {
      const startStr = item.start || '00:00';
      const endStr = item.end || '00:00';
      const [sh, sm] = startStr.split(':').map(Number);
      const [eh, em] = endStr.split(':').map(Number);
      return { ...item, startMin: sh * 60 + sm, endMin: eh * 60 + em };
    });

    if (isRunning) {
      const currentOrNext = intervals.find((i: any) => currentMinutes < i.endMin);
      return { label: 'Час зупинки', value: currentOrNext ? `План ${currentOrNext.end}` : lastReportTime || '—' };
    } else {
      const nextToStart = intervals.find((i: any) => i.startMin > currentMinutes);
      const currentInterval = intervals.find((i: any) => currentMinutes >= i.startMin && currentMinutes < i.endMin);
      
      if (currentInterval) return { label: 'Запуск планово', value: `в ${currentInterval.start}` };
      if (nextToStart) return { label: 'Запуск планово', value: `в ${nextToStart.start}` };
      
      // FALLBACK: If recently stopped (report today exists)
      if (isReportToday && (status.includes('не працює') || status.includes('стоп') || status.includes('зупинка'))) {
        return { label: 'Час зупинки', value: lastReportTime || '—' };
      }

      return { label: 'Запуск', value: 'не планується' };
    }
  };

  const planned = getPlannedTime();

  // --- Button Styles Logic ---
  const getBtnStyle = (section: 'schedule' | 'last_report' | 'shift') => {
    const isActive = openSection === section;
    let colorClass = "bg-slate-50 dark:bg-slate-800/40 border-slate-100 dark:border-slate-800 text-slate-400"; // Default Gray
    
    if (section === 'schedule') {
      if (data.is_not_working) colorClass = "bg-rose-50 dark:bg-rose-950/20 border-rose-100 dark:border-rose-900/30 text-rose-600 dark:text-rose-400";
      else if (data.current_schedule && data.current_schedule.length > 0) colorClass = "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/30 text-emerald-600 dark:text-emerald-400";
    } else if (section === 'last_report') {
      if (isReportToday) colorClass = "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/30 text-emerald-600 dark:text-emerald-400";
    } else if (section === 'shift') {
      if (data.current_shift_name) colorClass = "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900/30 text-emerald-600 dark:text-emerald-400";
    }

    // Override if active
    if (isActive) return `flex flex-col items-center justify-center py-2 rounded-xl border transition-all ring-2 ring-blue-500/20 bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 shadow-inner`;
    
    return `flex flex-col items-center justify-center py-2 rounded-xl border transition-all ${colorClass}`;
  };

  return (
    <motion.div
      initial={isNew ? { scale: 0.95, opacity: 0 } : { opacity: 0, y: 10 }}
      animate={{ 
        scale: isNew ? [1, 1.02, 1] : 1, 
        opacity: 1, 
        y: 0,
        borderWidth: isNew ? '3px' : '1px',
        borderColor: isNew ? glowHex : undefined,
        boxShadow: isNew ? `0 0 30px rgba(${glowRgba}, 0.4)` : '0 2px 4px -1px rgb(0 0 0 / 0.1)'
      }}
      transition={{ scale: isNew ? { repeat: Infinity, duration: 1.5 } : { duration: 0.2 } }}
      className={`bg-white dark:bg-slate-900 rounded-[1.5rem] p-4 border transition-all relative group ${isNew ? 'z-20' : 'border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-lg'}`}
    >
      {/* Header: Name and Time */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl ${theme.accent} relative`}>
            <Zap className={`h-5 w-5 ${theme.text}`} strokeWidth={2.5} />
            {(statusColor === 'green' || (isReportToday && (data.gpu_status || '').toLowerCase().includes('аваріями'))) && (
              <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
            )}
          </div>
          <div>
            <h3 className="font-black text-xl text-slate-900 dark:text-white leading-none tracking-tighter">
              {data.short_name || data.name}
            </h3>
            <span className={`text-[10px] font-black uppercase tracking-tight ${mainMode !== '—' ? 'text-[#004899] dark:text-blue-400' : 'text-slate-400'}`}>
              {mainMode}
            </span>
          </div>
        </div>
        <div className="text-right bg-slate-50 dark:bg-slate-800/50 px-2 py-1 rounded-lg border border-slate-100 dark:border-slate-800">
           <span className="text-[8px] font-black text-slate-400 uppercase block leading-none mb-0.5 tracking-widest">{planned.label}</span>
           <span className="text-[11px] font-black text-slate-700 dark:text-slate-200">{planned.value}</span>
        </div>
      </div>

      {/* Power Bar */}
      <div className="bg-slate-50 dark:bg-slate-800/30 p-3 rounded-xl border border-slate-100 dark:border-slate-800 mb-3">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[9px] uppercase font-black text-slate-400 flex items-center tracking-widest">
            <TrendingUp className="h-3 w-3 mr-1 text-amber-500" /> {data.load_power_percent || 0}%
          </span>
          <span className="text-[10px] font-black text-[#004899] dark:text-blue-400">{data.load_power_kw || 0} кВт</span>
        </div>
        <div className="w-full h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
          <motion.div initial={{ width: 0 }} animate={{ width: `${data.load_power_percent || 0}%` }} className={`h-full ${Number(data.load_power_percent) > 90 ? 'bg-rose-500' : 'bg-[#004899]'}`} />
        </div>
      </div>

      {/* Status Badge */}
      <div className={`flex items-center gap-2 p-2 rounded-xl border ${theme.border} ${theme.bg} mb-4`}>
        <Icon className={`h-4 w-4 ${theme.text}`} strokeWidth={2.5} />
        <span className={`text-[11px] font-black uppercase tracking-tight ${theme.text}`}>{detailStatus}</span>
      </div>

      {/* Interactive Expandable Sections */}
      <div className="grid grid-cols-3 gap-1.5">
        <button onClick={() => toggleSection('schedule')} className={getBtnStyle('schedule')}>
          <Calendar className="w-3.5 h-3.5 mb-1" />
          <span className="text-[8px] font-black uppercase tracking-tighter">Графік</span>
        </button>
        
        <button onClick={() => toggleSection('last_report')} className={getBtnStyle('last_report')}>
          <FileText className="w-3.5 h-3.5 mb-1" />
          <span className="text-[8px] font-black uppercase tracking-tighter">Звіт</span>
        </button>

        <button onClick={() => toggleSection('shift')} className={getBtnStyle('shift')}>
          <User className="w-3.5 h-3.5 mb-1" />
          <span className="text-[8px] font-black uppercase tracking-tighter">Зміна</span>
        </button>
      </div>

      {/* Expandable Content Area */}
      <AnimatePresence mode="wait">
        {openSection !== 'none' && (
          <motion.div
            key={openSection}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden bg-slate-50 dark:bg-slate-800/60 rounded-xl mt-2 border border-slate-100 dark:border-slate-700/50"
          >
            <div className="p-3">
              {openSection === 'schedule' && (
                <div className="space-y-1.5">
                  {data.is_not_working ? (
                    <p className="text-[10px] font-black text-rose-500 text-center uppercase tracking-widest">❌ НЕ ПРАЦЮЄ</p>
                  ) : data.current_schedule && data.current_schedule.length > 0 ? (
                    data.current_schedule.map((item: any, i: number) => (
                      <div key={i} className="flex justify-between text-[9px] font-bold text-slate-500 dark:text-slate-400">
                        <span>{item.start} - {item.end}</span>
                        <span className="text-slate-800 dark:text-slate-200">{item.power}%</span>
                      </div>
                    ))
                  ) : <p className="text-[9px] text-center text-slate-400 italic">Графік не подано</p>}
                </div>
              )}

              {openSection === 'last_report' && (
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[9px]">
                    <span className="font-black text-slate-400 uppercase tracking-tighter">Подав:</span>
                    <span className="font-black text-slate-700 dark:text-slate-200 truncate ml-2">{data.reported_by || '—'}</span>
                  </div>
                  <div className="flex justify-between items-center text-[9px]">
                    <span className="font-black text-slate-400 uppercase tracking-tighter">Час:</span>
                    <span className="font-black text-slate-700 dark:text-slate-200">{data.start_time || '—'}</span>
                  </div>
                </div>
              )}

              {openSection === 'shift' && (
                <div className="space-y-1">
                  <div className="flex flex-col">
                    <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1 leading-none">Зараз на зміні:</span>
                    <span className="text-[10px] font-black text-slate-800 dark:text-slate-200 leading-tight">
                      {data.current_shift_name || '—'}
                    </span>
                  </div>
                  {data.current_shift_phone && (
                    <a href={`tel:${data.current_shift_phone}`} className="flex items-center gap-1.5 text-[9px] font-black text-[#004899] dark:text-blue-400 mt-2 bg-blue-100/50 dark:bg-blue-900/20 px-2 py-1 rounded-lg w-fit hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors">
                      <Phone className="w-2.5 h-2.5" /> {data.current_shift_phone}
                    </a>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
