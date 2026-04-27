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
  History,
  Calendar,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

interface GPUCardProps {
  data: ObjectInfo;
  isNew?: boolean;
}

export default function GPUCard({ data, isNew }: GPUCardProps) {
  const [showSchedule, setShowSchedule] = useState(false);

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

  // Semantic Glow Colors
  const glowColors = {
    green: { rgba: '16, 185, 129', hex: '#10b981' },
    red: { rgba: '244, 63, 94', hex: '#f43f5e' },
    orange: { rgba: '245, 158, 11', hex: '#f59e0b' },
    blue: { rgba: '0, 72, 153', hex: '#004899' }
  }[statusColor];

  // Logic to separate Mode and Detailed Status
  const mainMode = (data.work_mode === 'Мережа' || data.work_mode === 'Острів') ? data.work_mode : '—';
  const detailStatus = data.gpu_status ? data.gpu_status.split(',')[0] : 'Очікування';

  // Dynamic Planned Time Logic
  const getPlannedTime = () => {
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    
    // Normalize date parsing: ensure UTC interpretation if no timezone is present
    const rawReportDate = data.last_report_at;
    let reportDate: Date | null = null;
    if (rawReportDate) {
      const isoDate = rawReportDate.includes('T') ? rawReportDate : rawReportDate.replace(' ', 'T') + 'Z';
      reportDate = new Date(isoDate);
    }
    
    const isReportToday = reportDate && reportDate.getUTCDate() === now.getUTCDate() && reportDate.getUTCMonth() === now.getUTCMonth();
    
    // STRICT Running check: must have a today's report AND active status
    const status = (data.gpu_status || '').toLowerCase();
    const isRunning = isReportToday && (status.includes('стабільна') || status.includes('аваріями'));
    
    const lastReportTime = (isReportToday && data.start_time) ? data.start_time : null;

    if (data.is_not_working) {
      return { label: 'Запуск', value: 'не планується' };
    }
    
    const explicitLabel = data.time_type === 'start' ? 'Час запуску' : 
                          data.time_type === 'stop' ? 'Час зупинки' : null;

    // CASE: NO SCHEDULE
    if (!data.current_schedule || data.current_schedule.length === 0) {
      if (!isRunning) {
        return { label: 'Запуск', value: 'не планується' };
      }
      return { 
        label: explicitLabel || 'Час зупинки', 
        value: lastReportTime || '—' 
      };
    }

    // CASE: HAS SCHEDULE
    const intervals = data.current_schedule.map((item: any) => {
      const startStr = item.start || '00:00';
      const endStr = item.end || '00:00';
      const [sh, sm] = startStr.split(':').map(Number);
      const [eh, em] = endStr.split(':').map(Number);
      return { ...item, startMin: sh * 60 + sm, endMin: eh * 60 + em };
    });

    if (isRunning) {
      // Find the interval we are currently in or the next one to finish
      const currentOrNext = intervals.find((i: any) => currentMinutes < i.endMin);
      
      if (currentOrNext) {
        return { label: 'Час зупинки', value: `План ${currentOrNext.end}` };
      }
      
      return { label: explicitLabel || 'Час зупинки', value: lastReportTime || '—' };
    } else {
      // NOT RUNNING
      // 1. Find the next interval that starts in the future
      const nextToStart = intervals.find((i: any) => i.startMin > currentMinutes);
      
      // 2. Find if we are currently inside an interval but not started yet
      const currentInterval = intervals.find((i: any) => currentMinutes >= i.startMin && currentMinutes < i.endMin);
      
      if (currentInterval) {
        return { label: 'Запуск планово', value: `в ${currentInterval.start}` };
      }

      if (nextToStart) {
        return { label: 'Запуск планово', value: `в ${nextToStart.start}` };
      }
      
      // 3. Fallback for just stopped
      if (isReportToday && (status.includes('не працює') || status.includes('стоп') || status.includes('зупинка'))) {
        return { label: 'Час зупинки', value: lastReportTime || '—' };
      }

      return { label: 'Запуск', value: 'не планується' };
    }
  };

  const planned = getPlannedTime();

  return (
    <motion.div
      initial={isNew ? { scale: 0.9, opacity: 0 } : { opacity: 0, y: 10 }}
      animate={{ 
        scale: isNew ? [1, 1.03, 1] : 1, 
        opacity: 1, 
        y: 0,
        borderWidth: isNew ? '3px' : '1px',
        borderColor: isNew ? glowColors.hex : undefined,
        boxShadow: isNew 
          ? [
              `0 0 0 0px rgba(${glowColors.rgba}, 0)`, 
              `0 0 40px 8px rgba(${glowColors.rgba}, 0.6)`, 
              `0 0 0 0px rgba(${glowColors.rgba}, 0)`
            ] 
          : '0 4px 6px -1px rgb(0 0 0 / 0.1)'
      }}
      transition={{
        scale: isNew ? { repeat: Infinity, duration: 1.2 } : { duration: 0.3 },
        boxShadow: isNew ? { repeat: Infinity, duration: 1.2 } : { duration: 0.3 },
        borderWidth: { duration: 0.2 }
      }}
      className={`bg-white dark:bg-slate-900 rounded-[2rem] p-6 border transition-all relative overflow-hidden group ${
        isNew 
          ? 'z-20 scale-105' 
          : 'border-slate-300 dark:border-slate-800 shadow-md hover:shadow-2xl'
      }`}
      style={{ borderColor: isNew ? glowColors.hex : undefined }}
    >
      {isNew && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute top-0 right-0 p-2"
        >
          <span className="flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75`} style={{ backgroundColor: glowColors.hex }}></span>
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: glowColors.hex }}></span>
          </span>
        </motion.div>
      )}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-2xl ${theme.accent} relative`}>
            <Zap className={`h-6 w-6 ${theme.text}`} strokeWidth={2.5} />
            {statusColor === 'green' && (
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            )}
          </div>
          <div className="group/name relative">
            <h3 
              className="font-black text-2xl text-slate-900 dark:text-white leading-none tracking-tighter cursor-help"
            >
              {data.short_name || data.name}
            </h3>
            {/* Tooltip on hover */}
            <div className="absolute left-0 top-full mt-2 hidden group-hover/name:block z-50 bg-slate-800 text-white text-[10px] py-1.5 px-3 rounded-lg shadow-xl whitespace-nowrap border border-slate-700 max-w-xs overflow-hidden text-ellipsis transition-colors">
              {data.name}
            </div>
          </div>
        </div>
        
        <div className="text-right">
           <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-0.5">
             {planned.label}
           </span>
           <span className="text-sm font-black text-slate-700 dark:text-slate-200 bg-slate-200 dark:bg-slate-800 px-2 py-1 rounded-lg whitespace-nowrap transition-colors">
             {planned.value}
           </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 mb-5">
        <div className="bg-slate-100 dark:bg-slate-800/50 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 transition-colors">
          <div className="flex justify-between items-end">
            <div>
              <p className="text-[10px] uppercase font-black text-slate-400 mb-1.5 flex items-center tracking-widest">
                <TrendingUp className="h-3 w-3 mr-1 text-[#f6c400]" /> Навантаження
              </p>
              <p className="text-xl font-black text-slate-800 dark:text-slate-200 transition-colors">
                {data.load_power_percent ? `${data.load_power_percent}%` : '0%'} 
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-bold text-[#004899] dark:text-blue-400 transition-colors">
                {data.load_power_kw ? `${data.load_power_kw} кВт` : '0 кВт'}
              </p>
            </div>
          </div>
          <div className="w-full h-1.5 bg-slate-300 dark:bg-slate-700 rounded-full mt-3 overflow-hidden">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${data.load_power_percent || 0}%` }}
              className={`h-full ${Number(data.load_power_percent) > 90 ? 'bg-rose-500' : 'bg-[#004899]'}`}
            />
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs px-1">
          <span className="font-bold text-slate-400 flex items-center gap-1">
            <Settings2 className="w-3.5 h-3.5" /> Режим:
          </span>
          <span className={`font-black transition-colors ${mainMode !== '—' ? 'text-[#004899] dark:text-blue-400' : 'text-slate-500'}`}>
            {mainMode}
          </span>
        </div>

        <div className={`flex flex-col gap-1 p-4 rounded-2xl border ${theme.border} ${theme.bg} shadow-sm transition-colors`}>
          <div className="flex items-center gap-2.5">
            <Icon className={`h-5 w-5 ${theme.text}`} strokeWidth={2.5} />
            <span className={`text-sm font-black uppercase tracking-tight ${theme.text}`}>
              {detailStatus}
            </span>
          </div>
          {/* Detailed sub-status */}
          {data.gpu_status && data.gpu_status.includes('(') && (
            <p className="text-[10px] font-bold text-slate-500 mt-1 leading-tight border-t border-black/5 dark:border-white/5 pt-1.5 italic">
              {data.gpu_status.substring(data.gpu_status.indexOf('('))}
            </p>
          )}
        </div>
      </div>

      {/* Schedule Section */}
      <div className="mt-4">
        <button 
          onClick={() => setShowSchedule(!showSchedule)}
          className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl transition-all border ${
            data.is_not_working 
              ? 'bg-rose-50/50 dark:bg-rose-900/10 border-rose-100 dark:border-rose-900/20 text-rose-600' 
              : data.current_schedule && data.current_schedule.length > 0
                ? 'bg-emerald-50/50 dark:bg-emerald-950/10 border-emerald-100 dark:border-emerald-900/20 text-emerald-600'
                : 'bg-slate-50 dark:bg-slate-800/40 border-slate-100 dark:border-slate-800 text-slate-400'
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          <span className="text-[10px] font-black uppercase tracking-widest">
            {data.is_not_working 
              ? 'План: НЕ ПРАЦЮЄ' 
              : data.current_schedule && data.current_schedule.length > 0
                ? 'Графік роботи'
                : 'Графік не подано'}
          </span>
          {showSchedule ? <ChevronUp className="w-3 h-3 ml-1 opacity-50" /> : <ChevronDown className="w-3 h-3 ml-1 opacity-50" />}
        </button>
        
        <AnimatePresence>
          {showSchedule && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="pt-3 pb-2 space-y-2">
                {data.is_not_working ? (
                  <div className="flex flex-col items-center justify-center py-4 bg-rose-50 dark:bg-rose-900/10 rounded-2xl border border-rose-100 dark:border-rose-900/20">
                    <XCircle className="h-6 w-6 text-rose-500 mb-2" />
                    <span className="text-xs font-black text-rose-600 uppercase tracking-widest">❌ НЕ ПРАЦЮЄ</span>
                    <span className="text-[9px] font-bold text-rose-400 mt-1 text-center">Згідно з графіком трейдера</span>
                  </div>
                ) : data.current_schedule && data.current_schedule.length > 0 ? (
                  data.current_schedule.map((item: any, i: number) => (
                    <div key={i} className="flex justify-between items-center text-[10px] bg-slate-50 dark:bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-100 dark:border-slate-800 transition-colors">
                      <span className="font-bold text-slate-500">
                        {item.time || `${item.start} - ${item.end}`}
                      </span>
                      <span className="font-black text-slate-800 dark:text-slate-200">
                        {item.power}% {item.mode ? `(${item.mode})` : ''}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-[10px] text-center text-slate-400 py-2 italic">Графік не подано</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-400 transition-colors">
          {data.reported_by ? data.reported_by[0] : '?'}
        </div>
        <div className="flex flex-col min-w-0">
          <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Останній звіт:</span>
          <span className="text-[11px] font-black text-slate-600 dark:text-slate-300 leading-tight">
            {data.reported_by || 'Система'}
          </span>
        </div>
      </div>
    </motion.div>
  );
}
