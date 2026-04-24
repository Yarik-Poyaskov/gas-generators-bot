'use client';

import { useEffect, useState, useMemo } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import GPUCard from '@/components/GPUCard';
import { ObjectInfo } from '@/types';
import api from '@/lib/api';
import { LayoutGrid, List, RefreshCw, Loader2, Search as SearchIcon, SortAsc, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type SortOption = 'alphabetical' | 'status' | 'power' | 'last_report';

export default function Dashboard() {
  const [objects, setObjects] = useState<ObjectInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [newReportId, setNewReportId] = useState<number | null>(null);
  const [viewType, setViewType] = useState<'grid' | 'list'>('grid');
  const [sortBy, setSortBy] = useState<SortOption>('status');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [showSortMenu, setShowSortBy] = useState(false);

  const fetchObjects = async () => {
    try {
      const response = await api.get('/data/objects');
      setObjects(response.data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch objects:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const savedView = localStorage.getItem('dashboard_view_type');
    if (savedView === 'grid' || savedView === 'list') {
      setViewType(savedView);
    }
    
    const token = localStorage.getItem('access_token');
    if (!token) {
      window.location.href = '/login';
      return;
    }

    fetchObjects();

    // Construct WebSocket URL dynamically
    let wsUrl = '';
    
    if (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL.startsWith('ws')) {
      wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}?token=${token}`;
    } else {
      // Fallback to dynamic detection based on current URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host; // includes port
      wsUrl = `${protocol}//${host}/api/ws/status?token=${token}`;
    }

    const socket = new WebSocket(wsUrl);

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'new_report') {
        fetchObjects();
        setNewReportId(message.data.obj_id);
        setTimeout(() => setNewReportId(null), 5000);
      }
    };

    return () => {
      socket.close();
    };
  }, []);

  const sortedObjects = useMemo(() => {
    const sorted = [...objects];
    
    const sortMultiplier = sortOrder === 'asc' ? 1 : -1;

    sorted.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'alphabetical':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'status':
          const getStatusWeight = (status: string | null = '') => {
            if (!status || status.toLowerCase().includes('очікування')) return 10; // Waiting - Last
            const s = status.toLowerCase();
            if (s.includes('аварії') || s.includes('не готова')) return 3;
            if (s.includes('не працює')) return 2;
            if (s.includes('стабільна')) return 0;
            return 4;
          };
          comparison = getStatusWeight(a.gpu_status) - getStatusWeight(b.gpu_status);
          break;
        case 'power':
          comparison = Number(b.load_power_percent || 0) - Number(a.load_power_percent || 0);
          break;
      }
      return comparison * sortMultiplier;
    });

    return sorted;
  }, [objects, sortBy, sortOrder]);

  const handleViewChange = (type: 'grid' | 'list') => {
    setViewType(type);
    localStorage.setItem('dashboard_view_type', type);
  };

  const sortLabels: Record<string, string> = {
    alphabetical: 'За алфавітом',
    status: 'За статусом (Стабільні перші)',
    power: 'За навантаженням'
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8">
        {/* Page Header Area */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
              Статус ГПУ
              <span className="px-2.5 py-1 bg-[#004899]/10 text-[#004899] text-xs font-black rounded-lg uppercase">Live</span>
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">
              Останнє оновлення: <span className="text-slate-900 dark:text-slate-200 font-bold">{lastUpdated.toLocaleTimeString()}</span>
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Sort Dropdown */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <button 
                  onClick={() => setShowSortBy(!showSortMenu)}
                  className="flex items-center gap-2 bg-white dark:bg-slate-900 px-4 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:border-[#004899]/30 transition-all text-sm font-bold text-slate-700 dark:text-slate-300"
                >
                  <SortAsc className="h-4 w-4 text-[#004899]" />
                  <span className="hidden sm:inline">{sortLabels[sortBy]}</span>
                  <ChevronDown className={`h-3 w-3 transition-transform ${showSortMenu ? 'rotate-180' : ''}`} />
                </button>
                
                <AnimatePresence>
                  {showSortMenu && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setShowSortBy(false)} />
                      <motion.div 
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute right-0 mt-2 w-64 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-100 dark:border-slate-800 py-2 z-20 overflow-hidden"
                      >
                        {(Object.keys(sortLabels) as SortOption[]).map((option) => (
                          <button
                            key={option}
                            onClick={() => { setSortBy(option); setShowSortBy(false); }}
                            className={`w-full text-left px-5 py-3 text-sm font-bold transition-colors ${sortBy === option ? 'text-[#004899] bg-blue-50 dark:bg-blue-900/20' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                          >
                            {sortLabels[option]}
                          </button>
                        ))}
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>

              {/* Sort Order Toggle */}
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="p-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm hover:bg-slate-50 dark:hover:bg-slate-800 transition-all text-[#004899]"
                title={sortOrder === 'asc' ? 'За зростанням' : 'За спаданням'}
              >
                {sortOrder === 'asc' ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" /></svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" /></svg>
                )}
              </button>
            </div>

            <div className="flex items-center gap-1 bg-white dark:bg-slate-900 p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <button 
                onClick={() => handleViewChange('grid')}
                className={`p-2 rounded-xl transition-all ${viewType === 'grid' ? 'bg-[#004899] text-white shadow-md' : 'text-slate-400 hover:bg-slate-50'}`}
              >
                <LayoutGrid className="h-4.5 w-4.5" />
              </button>
              <button 
                onClick={() => handleViewChange('list')}
                className={`p-2 rounded-xl transition-all ${viewType === 'list' ? 'bg-[#004899] text-white shadow-md' : 'text-slate-400 hover:bg-slate-50'}`}
              >
                <List className="h-4.5 w-4.5" />
              </button>
            </div>

            <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-1" />

            <button 
              onClick={() => {setLoading(true); fetchObjects();}}
              className="flex items-center gap-2 bg-white dark:bg-slate-900 px-4 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:border-[#004899]/30 transition-all active:scale-95 group"
            >
              <RefreshCw className={`h-4 w-4 text-[#004899] ${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
              <span className="text-sm font-bold text-slate-700 dark:text-slate-300">Оновити</span>
            </button>
          </div>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Усього ГПУ', value: objects.length, color: 'blue' },
            { label: 'У роботі', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('стабільна')).length, color: 'green' },
            { label: 'Зупинено', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('не працює')).length, color: 'red' },
            { label: 'Аварії / Інше', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('аварії') || (o.gpu_status || '').toLowerCase().includes('не готова')).length, color: 'orange' },
          ].map((stat, i) => (
            <div key={i} className="bg-white dark:bg-slate-900 p-4 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{stat.label}</p>
              <p className={`text-2xl font-black ${stat.color === 'green' ? 'text-emerald-600' : stat.color === 'red' ? 'text-rose-600' : stat.color === 'orange' ? 'text-amber-600' : 'text-[#004899]'}`}>
                {stat.value}
              </p>
            </div>
          ))}
        </div>

        {/* Content Area */}
        <AnimatePresence mode="wait">
          {loading && objects.length === 0 ? (
            <motion.div 
              key="loader"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-24"
            >
              <div className="relative">
                <div className="h-16 w-16 rounded-full border-4 border-slate-100 border-t-[#004899] animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="h-8 w-8 rounded-full bg-blue-50 flex items-center justify-center">
                    <RefreshCw className="h-4 w-4 text-[#004899] animate-pulse" />
                  </div>
                </div>
              </div>
              <p className="text-slate-500 font-bold mt-6 animate-pulse uppercase tracking-[0.2em] text-[10px]">Завантаження даних...</p>
            </motion.div>
          ) : viewType === 'grid' ? (
            <motion.div 
              key="grid-content"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 [.sidebar-collapsed_&]:lg:grid-cols-4 [.sidebar-collapsed_&]:xl:grid-cols-5 [.sidebar-collapsed_&]:2xl:grid-cols-6 gap-6"
            >
              {sortedObjects.map((obj) => (
                <GPUCard 
                  key={obj.id} 
                  data={obj} 
                  isNew={newReportId === obj.id}
                />
              ))}
            </motion.div>
          ) : (
            <motion.div
              key="list-content"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white dark:bg-slate-950 rounded-[2.5rem] border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                      <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Об'єкт</th>
                      <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Статус</th>
                      <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Навантаження</th>
                      <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Режим</th>
                      <th className="px-8 py-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Час</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {sortedObjects.map((obj) => (
                      <tr key={obj.id} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors group">
                        <td className="px-8 py-6 font-black text-slate-900 dark:text-white">
                          <div className="flex flex-col">
                            <span className="text-lg">{obj.short_name || obj.name}</span>
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tight truncate max-w-[150px]">{obj.name}</span>
                          </div>
                        </td>
                        <td className="px-8 py-6 text-center">
                          <span className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-tight shadow-sm
                            ${(obj.gpu_status || '').toLowerCase().includes('стабільна') ? 'bg-emerald-100 text-emerald-700 border border-emerald-200' : 
                              (obj.gpu_status || '').toLowerCase().includes('не працює') ? 'bg-rose-100 text-rose-700 border border-rose-200' : 
                              'bg-amber-100 text-amber-700 border border-amber-200'}`}
                          >
                            {(obj.gpu_status || 'Очікування')}
                          </span>
                        </td>
                        <td className="px-8 py-6 text-center">
                          <div className="flex flex-col items-center">
                            <span className="font-black text-slate-800 dark:text-slate-200 text-lg">{obj.load_power_percent || 0}%</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">{obj.load_power_kw || 0} кВт</span>
                          </div>
                        </td>
                        <td className="px-8 py-6">
                           <div className="flex flex-col">
                             <span className="text-xs font-black text-slate-700 dark:text-slate-300">{(obj.work_mode === 'Мережа' || obj.work_mode === 'Острів') ? obj.work_mode : '—'}</span>
                             <span className="text-[10px] text-slate-400 font-bold truncate max-w-[120px]">{obj.reported_by || '—'}</span>
                           </div>
                        </td>
                        <td className="px-8 py-6 text-right">
                          <div className="flex flex-col items-end">
                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-0.5">
                              {obj.time_type === 'start' ? 'Час запуску' : 'Час зупинки'}
                            </span>
                            <span className="text-xs font-black text-[#004899] dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-xl">
                              {obj.start_time || '—'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!loading && objects.length === 0 && (
          <div className="bg-white dark:bg-slate-900 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-[2.5rem] py-24 flex flex-col items-center justify-center text-center px-6">
            <div className="w-20 h-20 bg-slate-50 dark:bg-slate-800 rounded-3xl flex items-center justify-center mb-6 shadow-sm">
              <SearchIcon className="h-10 w-10 text-slate-300" />
            </div>
            <h3 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">Об'єктів не знайдено</h3>
            <p className="text-slate-500 dark:text-slate-400 max-w-xs mt-3 font-medium">
              Схоже, за вашим аккаунтом не закріплено жодного об'єкта або база даних наразі порожня.
            </p>
            <button 
              onClick={() => {setLoading(true); fetchObjects();}}
              className="mt-8 bg-[#004899] text-white px-6 py-3 rounded-2xl font-bold shadow-lg shadow-blue-500/20 hover:bg-[#003675] transition-all"
            >
              Перевірити ще раз
            </button>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
