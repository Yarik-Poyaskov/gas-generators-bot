'use client';

import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { SummaryReportData } from '@/types';
import api from '@/lib/api';
import { ClipboardList, RefreshCw, Loader2, Phone, User, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';

export default function SummaryShiftsPage() {
  const [data, setData] = useState<SummaryReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await api.get('/data/summary');
      setData(response.data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch summary data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getStatusStyle = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('стабільна')) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/30';
    if (s.includes('аварі')) return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border-amber-200 dark:border-amber-500/30';
    return 'bg-rose-100 text-red-700 dark:bg-rose-500/20 dark:text-rose-400 border-rose-200 dark:border-rose-500/30';
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm shadow-slate-200/50 dark:shadow-none">
          <div className="flex items-center gap-4">
            <div className="h-12 w-12 rounded-2xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-[#004899] dark:text-blue-400 shadow-inner">
              <ClipboardList className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">Звіт з черговими</h1>
              <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">Дані про активні зміни та статуси ГПУ з 01:00</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block mr-2">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none mb-1">Останнє оновлення</p>
              <p className="text-sm font-black text-slate-700 dark:text-slate-200 leading-none">{lastUpdated.toLocaleTimeString()}</p>
            </div>
            <button 
              onClick={fetchData}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-bold text-sm hover:bg-[#004899] dark:hover:bg-blue-50 transition-all shadow-lg shadow-slate-900/10 dark:shadow-none disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              <span>Оновити</span>
            </button>
          </div>
        </div>

        {/* Table Section */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-slate-50/50 dark:bg-slate-800/50 border-bottom border-slate-200 dark:border-slate-800">
                  <th className="px-6 py-4 text-center text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest w-12">№</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Об'єкт</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Режим</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Час запуску</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Потужність</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Статус</th>
                  <th className="px-6 py-4 text-left text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Черговий</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      <td colSpan={6} className="px-6 py-8">
                        <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded-full w-full"></div>
                      </td>
                    </tr>
                  ))
                ) : data.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400 font-medium italic">
                      Звітів за сьогодні поки немає
                    </td>
                  </tr>
                ) : (
                  data.map((item, index) => (
                    <motion.tr 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      key={item.id} 
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors group"
                    >
                      <td className="px-6 py-4 text-center text-xs font-black text-slate-400">
                        {index + 1}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-[#004899] transition-colors">
                            <MapPin className="h-4 w-4" />
                          </div>
                          <span className="font-bold text-slate-900 dark:text-white truncate max-w-[200px]" title={item.tc_name}>
                            {item.tc_name.match(/\((.*?)\)/)?.[1] || item.tc_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm font-bold text-slate-600 dark:text-slate-300">
                        {item.work_mode}
                      </td>
                      <td className="px-6 py-4 text-sm font-black text-slate-700 dark:text-slate-200">
                        {item.start_time}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="text-sm font-black text-slate-900 dark:text-white">{item.load_power_percent}%</span>
                          <span className="text-[10px] font-bold text-slate-400">{item.load_power_kw} кВт</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-[11px] font-black border ${getStatusStyle(item.gpu_status)}`}>
                          {item.gpu_status}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <div className="flex items-center gap-1.5">
                            <User className="h-3 w-3 text-slate-400" />
                            <span className="text-sm font-bold text-slate-700 dark:text-slate-200">
                              {item.duty_info.split('(')[0].trim()}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Phone className="h-3 w-3 text-slate-400" />
                            <span className="text-[11px] font-bold text-slate-400 tracking-tight">
                              {item.duty_info.match(/\((.*?)\)/)?.[1] || '—'}
                            </span>
                          </div>
                        </div>
                      </td>
                    </motion.tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
