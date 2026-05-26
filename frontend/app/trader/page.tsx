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
  Activity,
  Plus,
  Trash2,
  Settings2,
  Save
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ScheduleItem {
  db_name: string;
  is_not_working: boolean;
  selectedHours: number[]; // 0 to 23
  power: number;
  mode: 'Мережа' | 'Острів';
}

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
  
  const [viewDate, setViewDate] = useState(() => new Date().toLocaleDateString('en-CA'));
  const [schedules, setSchedules] = useState<any[]>([]);
  const [fetching, setFetching] = useState(false);
  const [showInput, setShowInput] = useState(false);

  // Стейты для ручного ввода
  const [activeTab, setActiveTab] = useState<'text' | 'manual'>('text');
  const [objects, setObjects] = useState<any[]>([]);
  const [manualSchedules, setManualSchedules] = useState<ScheduleItem[]>([]);
  const [objectsFetching, setObjectsFetching] = useState(false);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (!token) { window.location.href = '/login'; return; }
    fetchSchedules(viewDate);
    fetchObjects();
  }, [viewDate]);

  const fetchObjects = async () => {
    setObjectsFetching(true);
    try {
      const response = await api.get('/data/objects');
      setObjects(response.data);
    } catch (err) {
      console.error('Не вдалося завантажити об\'єкти', err);
    } finally {
      setObjectsFetching(false);
    }
  };

  const addObject = (name: string) => {
    if (manualSchedules.find(s => s.db_name === name)) return;
    setManualSchedules([...manualSchedules, {
      db_name: name,
      is_not_working: false,
      selectedHours: [],
      power: 100,
      mode: 'Мережа'
    }]);
  };

  const removeObject = (name: string) => {
    setManualSchedules(manualSchedules.filter(s => s.db_name !== name));
  };

  const toggleHour = (objName: string, hour: number) => {
    setManualSchedules(manualSchedules.map(s => {
      if (s.db_name !== objName) return s;
      const hours = s.selectedHours.includes(hour) 
        ? s.selectedHours.filter(h => h !== hour)
        : [...s.selectedHours, hour].sort((a, b) => a - b);
      return { ...s, selectedHours: hours, is_not_working: hours.length === 0 };
    }));
  };

  const updateProp = (objName: string, key: 'power' | 'mode' | 'is_not_working', value: any) => {
    setManualSchedules(manualSchedules.map(s => {
      if (s.db_name !== objName) return s;
      return { ...s, [key]: value };
    }));
  };

  const convertToIntervals = (hours: number[], power: number, mode: string) => {
    if (hours.length === 0) return [];
    const intervals = [];
    let start = hours[0];
    let prev = hours[0];

    for (let i = 1; i <= hours.length; i++) {
      if (i < hours.length && hours[i] === prev + 1) {
        prev = hours[i];
      } else {
        intervals.push({
          start: `${start.toString().padStart(2, '0')}:00`,
          end: `${(prev + 1).toString().padStart(2, '0')}:00`,
          power,
          mode
        });
        if (i < hours.length) {
          start = hours[i];
          prev = hours[i];
        }
      }
    }
    return intervals;
  };

  const handlePublishManual = async () => {
    if (manualSchedules.length === 0) return;
    setLoading(true);
    setError('');
    
    try {
      const items = manualSchedules.map(s => ({
        db_name: s.db_name,
        target_date: viewDate,
        is_not_working: s.is_not_working,
        intervals: s.is_not_working ? [] : convertToIntervals(s.selectedHours, s.power, s.mode)
      }));

      const response = await api.post('/data/trader/publish', {
        date_str: viewDate.split('-').reverse().join('/'),
        items
      });

      if (response.data.success) {
        setSuccess(true);
        setManualSchedules([]);
        setShowInput(false);
        fetchSchedules(viewDate);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        setError(response.data.error || 'Помилка публікації');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Помилка сервера');
    } finally {
      setLoading(false);
    }
  };

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
      const response = await api.post('/data/trader/publish', { 
        date_str: previewData.date,
        items: previewData.data 
      });
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
                className="bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-white rounded-xl px-5 py-2.5 text-sm font-black outline-none focus:ring-2 ring-amber-500 transition-all cursor-pointer border border-slate-200 dark:border-slate-800"
              />
             <button onClick={() => setShowInput(!showInput)}
                className="bg-[#004899] text-white px-6 py-2.5 rounded-xl text-sm font-black hover:bg-[#003675] active:scale-95 transition-all shadow-xl shadow-blue-500/10"
              >
                {showInput ? 'ЗАКРИТИ' : 'ДОДАТИ ГРАФІК'}
              </button>
          </div>
        </div>

        {error && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-2xl flex items-center gap-3 text-rose-500 font-bold mb-4">
            <AlertCircle className="w-5 h-5" /> {error}
          </motion.div>
        )}

        {success && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-2xl flex items-center gap-3 text-emerald-500 font-bold mb-4">
            <CheckCircle2 className="w-5 h-5" /> Графік успішно опубліковано!
          </motion.div>
        )}

        <AnimatePresence>
          {showInput && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden mb-4">
              <div className="bg-white dark:bg-slate-950 p-6 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-xl space-y-6">
                
                {/* Вкладки */}
                <div className="flex border-b border-slate-100 dark:border-slate-900 pb-3 justify-between items-center">
                  <div className="flex gap-4">
                    <button
                      onClick={() => setActiveTab('text')}
                      className={`text-sm font-black pb-2 px-1 border-b-2 transition-all ${
                        activeTab === 'text'
                          ? 'border-[#004899] text-[#004899] dark:border-amber-500 dark:text-amber-500'
                          : 'border-transparent text-slate-400 hover:text-slate-600'
                      }`}
                    >
                      📝 Розпізнати текст
                    </button>
                    <button
                      onClick={() => setActiveTab('manual')}
                      className={`text-sm font-black pb-2 px-1 border-b-2 transition-all ${
                        activeTab === 'manual'
                          ? 'border-[#004899] text-[#004899] dark:border-amber-500 dark:text-amber-500'
                          : 'border-transparent text-slate-400 hover:text-slate-600'
                      }`}
                    >
                      🖱️ Ручний ввід
                    </button>
                  </div>
                  
                  {activeTab === 'manual' && (
                    <div className="text-[11px] font-black text-amber-500 uppercase tracking-widest bg-amber-500/10 px-4 py-1.5 rounded-xl border border-amber-500/20">
                      Публікація на: {viewDate.split('-').reverse().join('.')}
                    </div>
                  )}
                </div>

                {/* Вкладка 1: Розпізнати текст */}
                {activeTab === 'text' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-50 dark:bg-slate-900/30 p-4 rounded-3xl border border-slate-100 dark:border-slate-900">
                      <textarea 
                        className="w-full h-36 p-4 bg-white dark:bg-slate-900 rounded-2xl outline-none font-mono text-sm resize-none text-slate-900 dark:text-white border border-slate-200 dark:border-slate-800"
                        placeholder="Вставте текст графіка..." 
                        value={text} 
                        onChange={(e) => setText(e.target.value)}
                      />
                      <button 
                        onClick={handleParse} 
                        disabled={loading}
                        className="w-full mt-3 bg-slate-900 dark:bg-amber-600 text-white py-3 rounded-xl font-black text-xs uppercase tracking-widest hover:bg-black dark:hover:bg-amber-500 transition-colors disabled:opacity-50"
                      >
                        {loading ? 'ОБРОБКА...' : 'РОЗПІЗНАТИ ТЕКСТ'}
                      </button>
                    </div>
                    <div className="bg-slate-900 p-6 rounded-3xl border border-white/5 flex flex-col justify-between shadow-2xl">
                       {previewData ? (
                         <>
                           <div className="flex justify-between items-center border-b border-white/5 pb-3 mb-3">
                              <span className="text-xs font-black text-amber-400 uppercase tracking-widest">ДАТА: {previewData.date}</span>
                              <button onClick={handleConfirm} className="bg-emerald-500 text-white px-6 py-2 rounded-xl text-xs font-black uppercase tracking-widest hover:bg-emerald-400 transition-colors">ОПУБЛІКУВАТИ</button>
                           </div>
                           <div className="max-h-36 overflow-y-auto text-[10px] text-slate-400 space-y-2 pr-2 custom-scrollbar">
                              {previewData.data.map((item: any, idx: number) => (
                                <div key={idx} className="flex justify-between border-b border-white/5 pb-1">
                                  <span className="text-white font-bold truncate max-w-[150px]">{item.db_name.replace('ТРЦ ', '').replace('ТЦ ', '')}:</span> 
                                  <span className="text-right">
                                    {item.is_not_working ? 
                                      <span className="text-rose-500 font-black">СТОП</span> : 
                                      item.intervals.map((i:any)=>`${i.start}-${i.end}`).join(', ')
                                    }
                                  </span>
                                </div>
                              ))}
                           </div>
                         </>
                       ) : <div className="h-full flex items-center justify-center text-slate-600 text-xs font-black uppercase">Очікування на текст...</div>}
                    </div>
                  </div>
                )}

                {/* Вкладка 2: Ручний ввід */}
                {activeTab === 'manual' && (
                  <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    
                    {/* Список объектов слева */}
                    <div className="lg:col-span-1 bg-slate-50 dark:bg-slate-900/30 rounded-3xl border border-slate-100 dark:border-slate-900 p-4 h-fit max-h-[450px] overflow-hidden flex flex-col">
                      <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                        <Plus className="w-3.5 h-3.5" /> Додати об'єкт
                      </h3>
                      <div className="flex lg:flex-col gap-1.5 overflow-x-auto lg:overflow-y-auto pb-2 lg:pb-0 pr-1 custom-scrollbar">
                        {objectsFetching ? (
                          <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-slate-300" /></div>
                        ) : (
                          objects.map(obj => {
                            const isAdded = manualSchedules.find(s => s.db_name === obj.name);
                            return (
                              <button
                                key={obj.id}
                                onClick={() => isAdded ? removeObject(obj.name) : addObject(obj.name)}
                                className={`shrink-0 px-3.5 py-2.5 rounded-xl font-bold text-xs transition-all flex justify-between items-center gap-2 border border-transparent ${
                                  isAdded 
                                  ? 'bg-[#004899] dark:bg-amber-500 text-white shadow-md' 
                                  : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-slate-200 dark:border-slate-800'
                                }`}
                              >
                                <span className="truncate">{obj.short_name || obj.name.replace('ТРЦ ', '').replace('ТЦ ', '')}</span>
                                {isAdded && <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>

                    {/* Редактор справа */}
                    <div className="lg:col-span-3 space-y-4 max-h-[450px] overflow-y-auto pr-1 custom-scrollbar">
                      {manualSchedules.length === 0 ? (
                        <div className="h-full min-h-[250px] border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl flex flex-col items-center justify-center text-slate-300 dark:text-slate-700 bg-slate-50/50 dark:bg-slate-900/10 p-12">
                          <Activity className="w-12 h-12 mb-3 opacity-20" />
                          <p className="font-black uppercase tracking-[0.2em] text-xs text-center">Оберіть об'єкти зліва для налаштування</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {manualSchedules.map((sched) => (
                            <div 
                              key={sched.db_name}
                              className="bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 relative group"
                            >
                              <button 
                                onClick={() => removeObject(sched.db_name)}
                                className="absolute top-4 right-4 p-1.5 text-slate-300 hover:text-rose-500 transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>

                              <div className="flex flex-col md:flex-row md:items-center gap-4 mb-4">
                                <div className="w-full md:w-44">
                                  <h4 className="text-sm font-black text-slate-900 dark:text-white leading-tight">
                                    {sched.db_name.replace('ТРЦ ', '').replace('ТЦ ', '')}
                                  </h4>
                                  <div className="flex gap-1.5 mt-1.5">
                                     <button 
                                       onClick={() => updateProp(sched.db_name, 'is_not_working', !sched.is_not_working)}
                                       className={`text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase transition-all ${
                                         sched.is_not_working 
                                         ? 'bg-rose-500 text-white' 
                                         : 'bg-white dark:bg-slate-800 text-slate-400 border border-slate-200 dark:border-slate-700'
                                       }`}
                                     >
                                       Стоп
                                     </button>
                                     <button 
                                       onClick={() => updateProp(sched.db_name, 'mode', sched.mode === 'Мережа' ? 'Острів' : 'Мережа')}
                                       className={`text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase transition-all ${
                                         sched.mode === 'Острів' 
                                         ? 'bg-amber-500 text-white' 
                                         : 'bg-blue-500 text-white'
                                       }`}
                                     >
                                       {sched.mode}
                                     </button>
                                  </div>
                                </div>

                                {!sched.is_not_working && (
                                  <div className="flex-1 flex flex-wrap gap-1">
                                    {[100, 95, 90, 80, 70, 50, 30].map(p => (
                                      <button
                                        key={p}
                                        onClick={() => updateProp(sched.db_name, 'power', p)}
                                        className={`px-2.5 py-0.5 rounded-md text-[10px] font-black transition-all ${
                                          sched.power === p 
                                          ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm' 
                                          : 'bg-white dark:bg-slate-900 text-slate-400 hover:bg-slate-100 border border-slate-200 dark:border-slate-800'
                                        }`}
                                      >
                                        {p}%
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {!sched.is_not_working && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2 text-[9px] font-black text-slate-400 uppercase tracking-widest">
                                    <Clock className="w-3 h-3" /> Години роботи (клікніть для активації):
                                  </div>
                                  <div className="grid grid-cols-8 md:grid-cols-12 gap-1">
                                    {Array.from({ length: 24 }).map((_, h) => (
                                      <button
                                        key={h}
                                        onClick={() => toggleHour(sched.db_name, h)}
                                        className={`aspect-square rounded-lg flex items-center justify-center text-[10px] font-black transition-all ${
                                          sched.selectedHours.includes(h)
                                          ? (sched.mode === 'Острів' ? 'bg-amber-500 text-white shadow-sm' : 'bg-blue-500 text-white shadow-sm')
                                          : 'bg-white dark:bg-slate-900 text-slate-300 dark:text-slate-700 hover:bg-slate-100 border border-slate-200 dark:border-slate-800'
                                        }`}
                                      >
                                        {h.toString().padStart(2, '0')}
                                      </button>
                                    ))}
                                  </div>
                                  
                                  {sched.selectedHours.length > 0 && (
                                    <div className="pt-1 flex items-center gap-2">
                                       <div className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase bg-emerald-500/10 px-2 py-0.5 rounded-md">
                                         Інтервали: {convertToIntervals(sched.selectedHours, sched.power, sched.mode).map(i => `${i.start}-${i.end}`).join(', ')}
                                       </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}

                          {/* Кнопка публикации внизу списка */}
                          <div className="pt-2 flex justify-end">
                            <button
                              onClick={handlePublishManual}
                              disabled={loading}
                              className="bg-emerald-500 hover:bg-emerald-600 disabled:bg-slate-300 text-white px-6 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest hover:shadow-lg hover:shadow-emerald-500/20 active:scale-95 transition-all flex items-center gap-2"
                            >
                              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                              Опублікувати ручний графік
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                  </div>
                )}

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
                  <div key={sched.id} className="group hover:bg-slate-50/80 dark:hover:bg-white/[0.03] transition-all px-4 md:px-8 py-4 md:py-2 flex flex-col md:flex-row md:items-center gap-4 md:gap-10">
                    
                    {/* 1. Object Header (Large Font) */}
                    <div className="w-full md:w-64 shrink-0 flex items-center justify-between md:block">
                      <div>
                        <div className="flex items-center gap-3">
                           <div className={`w-3 h-3 rounded-full ${sched.is_not_working ? 'bg-rose-500' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse'}`} />
                           <span className="font-black text-slate-900 dark:text-white text-[16px] tracking-tight truncate leading-none">{cleanName}</span>
                        </div>
                        <div className="ml-6 mt-1 text-[11px] font-bold text-slate-300 dark:text-slate-500 uppercase tracking-widest leading-none">
                           {sched.trader_name} • {timeStr}
                        </div>
                      </div>
                      {sched.is_not_working && (
                        <span className="block md:hidden text-[10px] font-black text-rose-500 uppercase tracking-[0.1em] bg-rose-50/50 dark:bg-rose-900/10 px-3 py-1 rounded-lg border border-rose-500/20">Не працює</span>
                      )}
                    </div>

                    {/* 2. Timeline with dynamic labels (Larger and Lighter) */}
                    <div className="flex-1 w-full relative pb-1 md:pb-5 pt-2">
                       <TimelineBar intervals={intervals} isNotWorking={sched.is_not_working} />
                       
                       {!sched.is_not_working && (
                         <div className="hidden md:block absolute inset-x-0 bottom-0 h-5">
                            {intervals.map((i:any, idx:number) => {
                              const startH = parseInt(i.start.split(':')[0]);
                              return (
                                <div key={idx} 
                                  className="absolute text-[13px] font-black text-slate-900 dark:text-white font-mono tracking-tighter"
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
                         <span className="hidden md:inline-block text-[12px] font-black text-rose-500 uppercase tracking-[0.2em] bg-rose-50 dark:bg-rose-900/10 px-4 py-1.5 rounded-xl border border-rose-500/20">Не працює</span>
                       ) : (
                         <div className="flex flex-col md:flex-row md:justify-end gap-2">
                            {/* Mobile-only interval detail list */}
                            <div className="flex flex-col gap-1.5 md:hidden w-full">
                              {intervals.map((i:any, idx:number) => (
                                <div key={idx} className="bg-slate-50 dark:bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between text-xs w-full">
                                  <div className="flex items-center gap-2">
                                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                                    <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{i.start} - {i.end}</span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-black text-slate-900 dark:text-white">{i.power}%</span>
                                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-md text-white ${i.mode === 'Острів' ? 'bg-amber-500' : 'bg-blue-500'}`}>{i.mode}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                            
                            {/* Desktop only badges */}
                            <div className="hidden md:flex flex-wrap md:justify-end gap-2">
                              {intervals.map((i:any, idx:number) => (
                                <div key={idx} className="bg-white dark:bg-slate-900 px-3 py-1 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-2">
                                   <span className="text-[13px] font-black text-slate-900 dark:text-slate-200">{i.power}%</span>
                                   <div className={`w-2 h-2 rounded-full ${i.mode === 'Острів' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                                </div>
                              ))}
                            </div>
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
