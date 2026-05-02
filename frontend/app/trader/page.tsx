'use client';

import { useState, useEffect, useMemo } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/api';
import { 
  Calendar, 
  Send, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  Type, 
  Eye,
  ArrowRight,
  Info,
  Clock,
  Zap,
  Activity
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Компонент для визуальной шкалы 24ч
const TimelineBar = ({ intervals, isNotWorking }: { intervals: any[], isNotWorking: boolean }) => {
  if (isNotWorking) return <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800/30 rounded-full opacity-10" />;

  const segments = [];
  for (let i = 0; i < 24; i++) {
    const hour = i;
    const hourStr = `${hour.toString().padStart(2, '0')}:00`;
    const nextHourStr = `${(hour + 1).toString().padStart(2, '0')}:00`;
    
    const activeInterval = intervals.find(int => {
      const startH = parseInt(int.start.split(':')[0]);
      const endH = parseInt(int.end.split(':')[0]) || 24;
      return hour >= startH && hour < endH;
    });

    segments.push(
      <div 
        key={i} 
        title={`${hourStr} - ${nextHourStr}${activeInterval ? ` (${activeInterval.power}%, ${activeInterval.mode})` : ''}`}
        className={`h-full flex-1 transition-all cursor-pointer hover:scale-y-[2.5] relative group/seg ${
          activeInterval 
            ? (activeInterval.mode === 'Острів' ? 'bg-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.4)]' : 'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.4)]') 
            : 'bg-slate-100 dark:bg-slate-800/50 hover:bg-slate-200 dark:hover:bg-slate-700'
        } ${i === 0 ? 'rounded-l-md' : ''} ${i === 23 ? 'rounded-r-md' : ''} border-r border-white/10 last:border-0`}
      >
         <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[11px] px-2.5 py-1 rounded opacity-0 group-hover/seg:opacity-100 pointer-events-none whitespace-nowrap z-30 font-black border border-white/10 shadow-2xl transition-all">
            {hourStr} - {nextHourStr}
         </div>
      </div>
    );
  }

  return (
    <div className="flex h-4 w-full gap-[1px] items-center">
      {segments}
    </div>
  );
};

export default function TraderPortal() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  
  const [viewDate, setViewDate] = useState(new Date().toISOString().split('T')[0]);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [fetching, setFetching] = useState(false);
  const [showInput, setShowInput] = useState(false);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (!token) { window.location.href = '/login'; return; }
    fetchSchedules(viewDate);
  }, [viewDate]);

  const fetchSchedules = async (date: string) => {
    setFetching(true);
    try {
      const response = await api.get(`/data/trader/schedules?date=${date}`);
      setSchedules(response.data);
    } catch (err) {
      console.error('Failed to fetch schedules', err);
    } finally {
      setFetching(false);
    }
  };

  const stats = useMemo(() => {
    const working = schedules.filter(s => !s.is_not_working).length;
    return { total: schedules.length, working, stopped: schedules.length - working };
  }, [schedules]);

  const handleParse = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const response = await api.post('/data/trader/parse', { text });
      if (response.data.success) setPreviewData(response.data);
      else setError(response.data.error || 'Помилка розпізнавання');
    } catch (err) { setError('Помилка сервера'); }
    finally { setLoading(false); }
  };

  const handleConfirm = async () => {
    if (!previewData) return;
    setLoading(true);
    try {
      const items = Object.entries(previewData.data).map(([name, intervals]: [any, any]) => ({
        db_name: name,
        target_date: previewData.date.split('.').reverse().join('-'),
        is_not_working: false,
        intervals: intervals.map((i: any) => {
          const [start, end] = i.time.split('-');
          return { start, end, power: i.power, mode: 'Мережа' };
        })
      }));
      const response = await api.post('/data/trader/publish', { items });
      if (response.data.success) {
        setSuccess(true);
        setShowInput(false);
        fetchSchedules(viewDate);
        setTimeout(() => setSuccess(false), 3000);
      }
    } catch (err) { setError('Помилка публікації'); }
    finally { setLoading(false); }
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-4 max-w-6xl mx-auto px-2 md:px-0">
        
        {/* Top Control Bar */}
        <div className="bg-white dark:bg-slate-950 p-4 px-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
             <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-2xl">
                <Activity className="w-6 h-6 text-amber-600" />
             </div>
             <div>
               <h1 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight">Графіки ГПУ</h1>
               <div className="flex items-center gap-4 mt-1">
                  <span className="text-sm font-bold text-slate-400">План: <span className="text-emerald-500 font-black text-base">{stats.working}</span></span>
                  <span className="text-sm font-bold text-slate-400">Стоп: <span className="text-rose-500 font-black text-base">{stats.stopped}</span></span>
               </div>
             </div>
          </div>

          <div className="flex items-center gap-3">
             <input type="date" value={viewDate} onChange={(e) => setViewDate(e.target.value)}
                className="bg-slate-900 text-white rounded-xl px-5 py-2.5 text-sm font-black outline-none focus:ring-2 ring-amber-500 transition-all cursor-pointer"
              />
             <button onClick={() => setShowInput(!showInput)}
                className="bg-[#004899] text-white px-6 py-2.5 rounded-xl text-sm font-black hover:bg-[#003675] active:scale-95 transition-all shadow-xl shadow-blue-500/10"
              >
                {showInput ? 'ЗАКРИТИ' : 'ДОДАТИ ГРАФІК'}
              </button>
          </div>
        </div>

        <AnimatePresence>
          {showInput && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div className="bg-white dark:bg-slate-950 p-6 rounded-[2rem] border border-slate-200 dark:border-slate-800 shadow-xl">
                    <textarea className="w-full h-32 p-4 bg-slate-50 dark:bg-slate-900 rounded-2xl outline-none font-mono text-sm resize-none"
                      placeholder="Вставте текст..." value={text} onChange={(e) => setText(e.target.value)}
                    />
                    <button onClick={handleParse} className="w-full mt-3 bg-slate-900 text-white py-3 rounded-xl font-black text-xs uppercase tracking-widest">РОЗПІЗНАТИ ТЕКСТ</button>
                  </div>
                  <div className="bg-slate-900 p-6 rounded-[2rem] border border-white/5 flex flex-col justify-between shadow-2xl">
                     {previewData ? (
                       <>
                         <div className="flex justify-between items-center border-b border-white/5 pb-3 mb-3">
                            <span className="text-xs font-black text-amber-400 uppercase tracking-widest">ДАТА: {previewData.date}</span>
                            <button onClick={handleConfirm} className="bg-emerald-500 text-white px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest">ОПУБЛІКУВАТИ</button>
                         </div>
                         <div className="max-h-24 overflow-y-auto text-[10px] text-slate-400 space-y-1 pr-2">
                            {Object.keys(previewData.data).map(n => <div key={n} className="flex justify-between border-b border-white/5 pb-1"><span className="text-white font-bold">{n}:</span> <span>{previewData.data[n].map((i:any)=>i.time).join(', ')}</span></div>)}
                         </div>
                       </>
                     ) : <div className="h-full flex items-center justify-center text-slate-600 text-xs font-black uppercase">Очікування...</div>}
                  </div>
               </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Timeline View */}
        <div className="bg-white dark:bg-slate-950 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden min-h-[500px]">
          <div className="px-8 py-4 border-b border-slate-100 dark:border-slate-900 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/30">
             <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-slate-400" />
                <h2 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-[0.3em]">Добовий розклад роботи</h2>
             </div>
             <div className="flex items-center gap-6 text-[10px] font-black uppercase tracking-widest">
                <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_5px_rgba(59,130,246,0.5)]" /> <span className="text-slate-400">Мережа</span></div>
                <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_5px_rgba(245,158,11,0.5)]" /> <span className="text-slate-400">Острів</span></div>
             </div>
          </div>

          <div className="divide-y divide-slate-100 dark:divide-slate-900">
            {fetching ? (
              <div className="py-24 flex flex-col items-center gap-4 text-slate-400"><Loader2 className="w-10 h-10 animate-spin text-blue-500" /><span className="text-xs font-black uppercase tracking-[0.5em]">Завантаження...</span></div>
            ) : schedules.length === 0 ? (
              <div className="py-32 text-center text-slate-300 dark:text-slate-700 font-black uppercase tracking-[0.4em] text-sm">Дані відсутні</div>
            ) : (
              schedules.map((sched) => {
                const intervals = JSON.parse(sched.schedule_json);
                const dbDate = sched.created_at.includes('Z') ? sched.created_at : sched.created_at.replace(' ', 'T') + 'Z';
                const timeStr = new Date(dbDate).toLocaleTimeString('uk-UA', {hour: '2-digit', minute:'2-digit'});
                const cleanName = sched.tc_name.replace('ТРЦ ', '').replace('ТЦ ', '').replace('Епіцентр ', '');

                return (
                  <div key={sched.id} className="group hover:bg-slate-50/80 dark:hover:bg-white/[0.03] transition-all px-8 py-2 flex flex-col md:flex-row md:items-center gap-6 md:gap-10">
                    
                    {/* 1. Object Header (Large Font) */}
                    <div className="w-full md:w-64 shrink-0">
                      <div className="flex items-center gap-3">
                         <div className={`w-3 h-3 rounded-full ${sched.is_not_working ? 'bg-rose-500' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse'}`} />
                         <span className="font-black text-slate-900 dark:text-white text-[16px] tracking-tight truncate leading-none">{cleanName}</span>
                      </div>
                      <div className="ml-6 mt-1 text-[11px] font-bold text-slate-300 dark:text-slate-500 uppercase tracking-widest leading-none">
                         {sched.trader_name} • {timeStr}
                      </div>
                    </div>

                    {/* 2. Timeline with dynamic labels (Larger and Lighter) */}
                    <div className="flex-1 min-w-[300px] relative pb-5 pt-2">
                       <TimelineBar intervals={intervals} isNotWorking={sched.is_not_working} />
                       
                       {!sched.is_not_working && (
                         <div className="absolute inset-x-0 bottom-0 h-5">
                            {intervals.map((i:any, idx:number) => {
                              const startH = parseInt(i.start.split(':')[0]);
                              return (
                                <div key={idx} 
                                  className="absolute text-[11px] font-black text-slate-300 dark:text-slate-700 font-mono tracking-tighter"
                                  style={{ left: `${(startH / 24) * 100}%` }}
                                >
                                  {i.start}-{i.end}
                                </div>
                              );
                            })}
                         </div>
                       )}
                    </div>

                    {/* 3. Detailed Stats (Large Font) */}
                    <div className="w-full md:w-56 shrink-0 md:text-right">
                       {sched.is_not_working ? (
                         <span className="text-[12px] font-black text-rose-500 uppercase tracking-[0.2em] bg-rose-50 dark:bg-rose-900/10 px-4 py-1.5 rounded-xl border border-rose-500/20">Відключено</span>
                       ) : (
                         <div className="flex flex-wrap md:justify-end gap-2">
                            {intervals.map((i:any, idx:number) => (
                              <div key={idx} className="bg-white dark:bg-slate-900 px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-2">
                                 <span className="text-[13px] font-black text-slate-900 dark:text-slate-200">{i.power}%</span>
                                 <div className={`w-2 h-2 rounded-full ${i.mode === 'Острів' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                              </div>
                            ))}
                         </div>
                       )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Legend */}
        <div className="flex justify-between items-center px-6 text-[10px] font-bold text-slate-400 uppercase tracking-widest opacity-60">
           <div className="flex items-center gap-3">
              <Info className="w-3.5 h-3.5" /> Дані синхронізовані в реальному часі
           </div>
           <div>ОНОВЛЕНО: {new Date().toLocaleTimeString()}</div>
        </div>

      </div>
    </DashboardLayout>
  );
}
