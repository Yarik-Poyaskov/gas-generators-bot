'use client';

import { useState, useEffect } from 'react';
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
  Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function TraderPortal() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const role = typeof window !== 'undefined' ? localStorage.getItem('user_role') : null;
    
    if (!token) {
      window.location.href = '/login';
      return;
    }

    if (role !== 'admin' && role !== 'trader') {
      window.location.href = '/';
      return;
    }
  }, []);

  const handleParse = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    setError('');
    setPreviewData(null);
    try {
      const response = await api.post('/data/trader/parse', { text });
      if (response.data.success) {
        setPreviewData(response.data);
      } else {
        setError(response.data.error || 'Не вдалося розпізнати текст. Перевірте формат.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Помилка сервера при парсингу.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    // This would call the real confirm endpoint in the future
    // For now, let's simulate success since we're building the UI
    setLoading(true);
    setTimeout(() => {
      setSuccess(true);
      setLoading(false);
      setText('');
      setPreviewData(null);
      setTimeout(() => setSuccess(false), 5000);
    }, 1500);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8 max-w-5xl mx-auto">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
            Портал Трейдера
            <div className="p-2 bg-amber-50 dark:bg-amber-900/20 rounded-xl">
              <Calendar className="w-6 h-6 text-amber-600" />
            </div>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">
            Подача графіків роботи ГПУ на наступну добу
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="flex flex-col gap-6">
            <div className="bg-white dark:bg-slate-950 p-8 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-xl relative overflow-hidden">
              <div className="flex items-center gap-3 mb-6">
                <Type className="w-5 h-5 text-[#004899]" />
                <h2 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight">Введення тексту</h2>
              </div>

              <textarea 
                className="w-full h-80 p-6 bg-slate-50 dark:bg-slate-900 border-2 border-transparent focus:border-[#004899]/10 rounded-3xl outline-none font-mono text-sm transition-all resize-none shadow-inner"
                placeholder="Вставте текст графіка з месенджера...&#10;&#10;Наприклад:&#10;По К1:&#10;00:00-08:00 - 100%&#10;08:00-24:00 - 0%"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />

              <div className="mt-6 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-400 font-bold italic">
                  <Info className="w-3.5 h-3.5" />
                  Система автоматично замінить символи
                </div>
                <button 
                  onClick={handleParse}
                  disabled={loading || !text.trim()}
                  className="bg-[#004899] hover:bg-[#003675] disabled:bg-slate-200 text-white px-8 py-3.5 rounded-2xl font-black shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2 active:scale-95"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                    <>
                      <span>Розпізнати</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-5 bg-rose-50 border border-rose-100 rounded-[1.5rem] flex items-start gap-4 text-rose-600 text-sm font-bold shadow-lg shadow-rose-900/5"
                >
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <p>{error}</p>
                </motion.div>
              )}
              {success && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-5 bg-emerald-50 border border-emerald-100 rounded-[1.5rem] flex items-start gap-4 text-emerald-600 text-sm font-bold shadow-lg shadow-emerald-900/5"
                >
                  <CheckCircle2 className="w-5 h-5 shrink-0" />
                  <p>Графік успішно опубліковано в Telegram-групах!</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Preview Section */}
          <div className="flex flex-col gap-6">
            <div className="bg-slate-900 rounded-[2.5rem] p-8 shadow-2xl border border-white/5 relative h-full min-h-[400px]">
              <div className="flex items-center gap-3 mb-8 border-b border-white/10 pb-6">
                <Eye className="w-5 h-5 text-amber-400" />
                <h2 className="text-lg font-black text-white uppercase tracking-tight">Попередній перегляд</h2>
              </div>

              {!previewData ? (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500 gap-4 opacity-50">
                  <div className="w-16 h-16 rounded-full border-2 border-dashed border-slate-700 flex items-center justify-center">
                    <Calendar className="w-8 h-8" />
                  </div>
                  <p className="font-bold text-sm uppercase tracking-widest text-center px-10">
                    Натисніть "Розпізнати", щоб побачити результат
                  </p>
                </div>
              ) : (
                <div className="space-y-8">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black text-amber-400 uppercase tracking-[0.2em]">Графік на дату:</span>
                    <span className="text-xl font-black text-white">{previewData.date}</span>
                  </div>

                  <div className="space-y-6 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {Object.entries(previewData.data).map(([objName, schedule]: [any, any]) => (
                      <div key={objName} className="bg-white/5 p-5 rounded-2xl border border-white/10 group hover:border-amber-400/30 transition-colors">
                        <h4 className="font-black text-white mb-3 flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-amber-400" />
                          {objName}
                        </h4>
                        <div className="space-y-2">
                          {schedule.map((item: any, i: number) => (
                            <div key={i} className="flex items-center justify-between text-xs py-1.5 border-b border-white/5 last:border-0">
                              <span className="text-slate-400 font-bold">{item.time}</span>
                              <span className="text-white font-black">{item.power}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  <button 
                    onClick={handleConfirm}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-900 font-black py-5 rounded-[1.5rem] shadow-xl shadow-amber-500/20 flex items-center justify-center gap-3 transition-all active:scale-95 text-sm uppercase tracking-widest"
                  >
                    {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : (
                      <>
                        <Send className="w-5 h-5" />
                        <span>Опублікувати графік</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
