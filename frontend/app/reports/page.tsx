'use client';

import { useEffect, useState } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import { ReportInfo } from '@/types';
import api from '@/lib/api';
import { 
  FileText, 
  Search, 
  Filter, 
  Download, 
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ReportsHistory() {
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const reportsPerPage = 20;

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      window.location.href = '/login';
      return;
    }
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const response = await api.get('/data/reports', {
        params: { limit: reportsPerPage, offset: page * reportsPerPage }
      });
      setReports(response.data);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredReports = reports.filter(r => 
    r.tc_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.reported_by.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.gpu_status || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1">
            <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
              Історія звітів
              <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                <FileText className="w-6 h-6 text-[#004899]" />
              </div>
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">
              Перегляд та фільтрація всіх поданих звітів ГПУ
            </p>
          </div>

          <button className="flex items-center justify-center gap-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-6 py-3 rounded-2xl font-bold text-slate-700 dark:text-slate-300 shadow-sm hover:border-[#004899]/30 transition-all">
            <Download className="w-4 h-4" />
            Експорт в Excel
          </button>
        </div>

        {/* Filters Area */}
        <div className="bg-white dark:bg-slate-950 p-6 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-xl flex flex-col md:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-slate-400" />
            <input 
              type="text"
              placeholder="Пошук за об'єктом, статусом або оператором..."
              className="w-full pl-11 pr-4 py-3.5 bg-slate-50 dark:bg-slate-900 border-2 border-transparent focus:border-[#004899]/10 rounded-2xl outline-none font-medium text-sm transition-all"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <div className="flex items-center gap-3 w-full md:w-auto">
            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-50 dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 font-bold text-slate-600 dark:text-slate-400 text-sm hover:bg-slate-100 transition-all">
              <CalendarIcon className="w-4 h-4" />
              Всі дати
            </button>
            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-50 dark:bg-slate-900 rounded-2xl border border-slate-100 dark:border-slate-800 font-bold text-slate-600 dark:text-slate-400 text-sm hover:bg-slate-100 transition-all">
              <Filter className="w-4 h-4" />
              Фільтри
            </button>
          </div>
        </div>

        {/* Table Area */}
        <div className="bg-white dark:bg-slate-950 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden relative">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-800">
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Дата та час</th>
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Об'єкт</th>
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Статус</th>
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Навантаження</th>
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Оператор</th>
                  <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Дії</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                <AnimatePresence mode="popLayout">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-8 py-20 text-center">
                        <div className="flex flex-col items-center justify-center">
                          <Loader2 className="w-10 h-10 text-[#004899] animate-spin mb-4" />
                          <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Завантаження історії...</p>
                        </div>
                      </td>
                    </tr>
                  ) : filteredReports.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-8 py-20 text-center">
                        <p className="text-slate-400 font-bold">Нічого не знайдено за вашим запитом</p>
                      </td>
                    </tr>
                  ) : (
                    filteredReports.map((report, idx) => (
                      <motion.tr 
                        key={report.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: idx * 0.03 }}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50 transition-colors group"
                      >
                        <td className="px-8 py-5">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-900 dark:text-white text-sm">
                              {new Date(report.timestamp).toLocaleDateString()}
                            </span>
                            <span className="text-[10px] font-bold text-slate-400">
                              {new Date(report.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <span className="font-black text-slate-700 dark:text-slate-300 text-sm">
                            {report.tc_name.replace(/\((.*?)\)/, '$1')}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-center">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tight
                            ${(report.gpu_status || '').toLowerCase().includes('стабільна') ? 'bg-emerald-100 text-emerald-700' : 
                              (report.gpu_status || '').toLowerCase().includes('не працює') ? 'bg-rose-100 text-rose-700' : 
                              'bg-amber-100 text-amber-700'}`}
                          >
                            {report.gpu_status || '—'}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-center font-black text-slate-700 dark:text-slate-300">
                          {report.load_power_percent ? `${report.load_power_percent}%` : '—'}
                        </td>
                        <td className="px-8 py-5 font-bold text-slate-600 dark:text-slate-400 text-xs">
                          {report.reported_by}
                        </td>
                        <td className="px-8 py-5 text-right">
                          <button className="p-2 text-slate-400 hover:text-[#004899] transition-colors">
                            <ExternalLink className="w-4 h-4" />
                          </button>
                        </td>
                      </motion.tr>
                    ))
                  )}
                </AnimatePresence>
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-6 bg-slate-50/50 dark:bg-slate-900/30 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Сторінка {page + 1}
            </p>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setPage(prev => Math.max(0, prev - 1))}
                disabled={page === 0 || loading}
                className="p-2.5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 disabled:opacity-30 hover:bg-slate-50 transition-all shadow-sm"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button 
                onClick={() => setPage(prev => prev + 1)}
                disabled={reports.length < reportsPerPage || loading}
                className="p-2.5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 disabled:opacity-30 hover:bg-slate-50 transition-all shadow-sm"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
