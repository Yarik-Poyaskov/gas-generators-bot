'use client';

import { useState, useEffect } from 'react';
import { 
  X, 
  FileText, 
  User, 
  Calendar, 
  Activity, 
  Zap, 
  ShieldAlert,
  Thermometer,
  Gauge,
  History
} from 'lucide-react';
import api from '@/lib/api';

// Helper component to load Telegram images with bearer auth
function TelegramImage({ fileId, alt, className }: { fileId: string; alt: string; className?: string }) {
  const [src, setSrc] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    if (!fileId) return;

    setLoading(true);
    setError(false);

    api.get(`/data/media/${fileId}`, { responseType: 'blob' })
      .then(res => {
        const url = URL.createObjectURL(res.data);
        setSrc(url);
      })
      .catch(err => {
        console.error('Failed to load image:', err);
        setError(true);
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      if (src) {
        URL.revokeObjectURL(src);
      }
    };
  }, [fileId]);

  if (loading) {
    return (
      <div className={`flex flex-col items-center justify-center bg-slate-100 dark:bg-slate-800 animate-pulse rounded-2xl ${className}`}>
        <span className="text-[10px] font-bold text-slate-400">Завантаження фото...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-slate-100 dark:bg-slate-800 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 ${className}`}>
        <span className="text-[10px] font-bold text-rose-500">Помилка завантаження фото</span>
      </div>
    );
  }

  return (
    <img 
      src={src} 
      alt={alt} 
      className={`${className} object-contain rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-lg transition-shadow bg-slate-50 dark:bg-slate-900`} 
    />
  );
}

interface ChecklistModalProps {
  objectId: number | null;
  objectName: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChecklistModal({ objectId, objectName, isOpen, onClose }: ChecklistModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [showAnyway, setShowAnyway] = useState(false);

  useEffect(() => {
    if (isOpen && objectId) {
      setLoading(true);
      setError(null);
      setData(null);
      setShowAnyway(false);
      
      api.get(`/data/objects/${objectId}/latest-checklist`)
        .then(res => {
          setData(res.data);
          if (res.data && res.data.is_today) {
            setShowAnyway(true);
          }
        })
        .catch(err => {
          console.error(err);
          setError('Помилка завантаження даних');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, objectId]);

  if (!isOpen) return null;

  // Formatting helper for UTC date string
  const formatReportDate = (utcString: string) => {
    try {
      const isoStr = utcString.includes('T') ? utcString : utcString.replace(' ', 'T') + 'Z';
      const d = new Date(isoStr);
      // Format as DD.MM.YYYY HH:MM
      const pad = (n: number) => n.toString().padStart(2, '0');
      return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch {
      return utcString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="bg-white dark:bg-slate-900 rounded-[2rem] border border-slate-200 dark:border-slate-800 w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl relative z-10 overflow-hidden transition-all">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-500/10 rounded-2xl text-blue-500">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xl font-black text-slate-950 dark:text-white leading-none">
                Детальний Чек-лист
              </h3>
              <p className="text-xs font-bold text-slate-400 mt-1 uppercase tracking-wider">
                {objectName || 'Об\'єкт ГПУ'}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-10 h-10 border-4 border-[#004899] border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs font-bold text-slate-400 mt-3 uppercase tracking-wider">Завантаження чек-листа...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-8 text-rose-500">
              <ShieldAlert className="w-12 h-12 mb-3" />
              <p className="text-sm font-black">{error}</p>
            </div>
          )}

          {!loading && !error && data && !data.has_report && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <FileText className="w-16 h-16 mb-4 opacity-30" />
              <p className="text-sm font-bold text-center italic max-w-sm">
                Детальних звітів (чек-листів) по цьому об'єкту ще не заповнювалось.
              </p>
            </div>
          )}

          {!loading && !error && data && data.has_report && (
            <>
              {/* Warning if NOT today's report */}
              {!data.is_today && !showAnyway && (
                <div className="p-5 bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-[1.5rem] flex flex-col items-center text-center space-y-4">
                  <ShieldAlert className="w-10 h-10 text-amber-500" />
                  <div>
                    <h4 className="text-sm font-black text-amber-800 dark:text-amber-300">
                      За поточну дату звіту немає
                    </h4>
                    <p className="text-[11px] font-bold text-amber-600 dark:text-amber-400 mt-1 max-w-md leading-relaxed">
                      Сьогодні повний чек-лист для цього об'єкта не заповнювався. Ви можете переглянути попередній збережений звіт.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowAnyway(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-xs font-black uppercase tracking-wider rounded-xl transition-colors shadow-md hover:shadow-lg"
                  >
                    <History className="w-4 h-4" /> Показати крайній Чек-лист
                  </button>
                </div>
              )}

              {/* Checklist Data Display */}
              {showAnyway && (
                <div className="space-y-6">
                  {/* Operator Info */}
                  <div className="flex flex-wrap gap-4 items-center justify-between bg-slate-50 dark:bg-slate-800/40 p-4 rounded-[1.5rem] border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-sm font-black text-slate-500 dark:text-slate-400">
                        <User className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Заповнив:</p>
                        <p className="text-sm font-black text-slate-800 dark:text-slate-200">
                          {data.report.full_name || 'Оператор'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-slate-400" />
                      <span className="text-xs font-bold text-slate-500 dark:text-slate-400">
                        {formatReportDate(data.report.created_at)}
                      </span>
                    </div>
                  </div>

                  {/* 8 points checklist */}
                  <div>
                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                      Параметри перевірки:
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      
                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">1. Напруга АКБ</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.battery_voltage || '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">2. Тиск антифризу (До)</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.pressure_before != null ? `${data.report.pressure_before} бар` : '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">3. Тиск антифризу (Після)</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.pressure_after != null ? `${data.report.pressure_after} бар` : '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">4. Всього вироблено</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.total_mwh != null ? `${data.report.total_mwh} МВт*год` : '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">5. Всього відпрацьовано</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.total_hours != null ? `${data.report.total_hours} м/год` : '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">6. До відбору оливи</span>
                        <span className="font-black text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-800 px-2 py-1 rounded border border-slate-200/50 dark:border-slate-700/50">
                          {data.report.oil_sampling_limit != null ? `${data.report.oil_sampling_limit} м/год` : '—'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">7. Звірка апаратів</span>
                        <span className="font-black text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/20 px-2 py-1 rounded border border-emerald-100 dark:border-emerald-900/30">
                          Підтверджено
                        </span>
                      </div>

                      <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/20 rounded-xl border border-slate-100 dark:border-slate-800 text-xs">
                        <span className="font-bold text-slate-400">8. Статус роботи</span>
                        <span className="font-black text-[#004899] dark:text-blue-400 bg-blue-50 dark:bg-blue-950/20 px-2 py-1 rounded border border-blue-100 dark:border-blue-900/30 leading-none">
                          {data.report.gpu_status || '—'}
                        </span>
                      </div>

                    </div>
                  </div>

                  {/* Photos Section */}
                  <div>
                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                      Фотоматеріали:
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">
                          Фото мультиметра:
                        </span>
                        {data.report.photo_multimeter_id ? (
                          <TelegramImage 
                            fileId={data.report.photo_multimeter_id} 
                            alt="Фото мультиметра" 
                            className="w-full aspect-[4/3] rounded-2xl" 
                          />
                        ) : (
                          <div className="flex items-center justify-center bg-slate-100 dark:bg-slate-800 rounded-2xl w-full aspect-[4/3] text-[10px] font-bold text-slate-400 italic">
                            Фото відсутнє
                          </div>
                        )}
                      </div>

                      <div className="space-y-1.5">
                        <span className="text-[10px] font-black uppercase text-slate-400 tracking-wider">
                          Фото ШОС:
                        </span>
                        {data.report.photo_shos_id ? (
                          <TelegramImage 
                            fileId={data.report.photo_shos_id} 
                            alt="Фото ШОС" 
                            className="w-full aspect-[4/3] rounded-2xl" 
                          />
                        ) : (
                          <div className="flex items-center justify-center bg-slate-100 dark:bg-slate-800 rounded-2xl w-full aspect-[4/3] text-[10px] font-bold text-slate-400 italic">
                            Фото відсутнє
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              )}
            </>
          )}

        </div>
      </div>
    </div>
  );
}
