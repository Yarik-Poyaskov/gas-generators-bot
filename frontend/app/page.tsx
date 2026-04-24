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
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'stable' | 'stopped' | 'emergency'>('all');

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
    // 1. Filter by status dot
    let filtered = [...objects];
    
    if (statusFilter === 'stable') {
      filtered = filtered.filter(o => (o.gpu_status || '').toLowerCase().includes('стабільна'));
    } else if (statusFilter === 'stopped') {
      filtered = filtered.filter(o => (o.gpu_status || '').toLowerCase().includes('не працює'));
    } else if (statusFilter === 'emergency') {
      filtered = filtered.filter(o => (o.gpu_status || '').toLowerCase().includes('аварі') || (o.gpu_status || '').toLowerCase().includes('не готова'));
    }

    // 2. Filter by search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(o => 
        o.name.toLowerCase().includes(q) || 
        (o.short_name || '').toLowerCase().includes(q)
      );
    }

    // 3. Sort
    const sortMultiplier = sortOrder === 'asc' ? 1 : -1;

    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'alphabetical':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'status':
          const getStatusWeight = (status: string | null = '') => {
            if (!status || status.toLowerCase().includes('очікування')) return 10; // Waiting - Last
            const s = status.toLowerCase();
            if (s.includes('аварі') || s.includes('не готова')) return 3;
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

    return filtered;
  }, [objects, sortBy, sortOrder, searchQuery, statusFilter]);

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
    <DashboardLayout 
      searchQuery={searchQuery}
      setSearchQuery={setSearchQuery}
      headerCenterContent={
        <div className="flex items-center gap-4 lg:gap-8">
          {/* Title & Time Group */}
          <div className="flex items-center gap-4">
            <div className="flex flex-col">
              <h1 className="text-sm font-black text-slate-900 dark:text-white leading-none tracking-tight flex items-center gap-2">
                Статус ГПУ
                <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-[#004899] dark:text-blue-400 text-[8px] font-black rounded uppercase">Live</span>
              </h1>
              <p className="text-slate-400 text-[9px] font-bold mt-1">
                {lastUpdated.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
              </p>
            </div>
            <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-1 hidden lg:block" />
          </div>

          {/* Interactive Compact Stats - Clickable filters */}
          <div className="flex items-center gap-1 bg-slate-100/50 dark:bg-slate-800/40 p-1 rounded-2xl border border-slate-200/60 dark:border-slate-800/60 shadow-inner">
            {[
              { id: 'all', label: 'Усього', value: objects.length, color: 'blue', bg: 'bg-blue-500' },
              { id: 'stable', label: 'Робота', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('стабільна')).length, color: 'green', bg: 'bg-emerald-500' },
              { id: 'stopped', label: 'Стоп', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('не працює')).length, color: 'red', bg: 'bg-rose-500' },
              { id: 'emergency', label: 'Аварія', value: objects.filter(o => (o.gpu_status || '').toLowerCase().includes('аварі') || (o.gpu_status || '').toLowerCase().includes('не готова')).length, color: 'orange', bg: 'bg-amber-500' },
            ].map((stat) => (
              <button 
                key={stat.id} 
                onClick={() => setStatusFilter(stat.id as any)}
                className={`flex items-center gap-2 px-2.5 py-1.5 rounded-xl transition-all group relative ${statusFilter === stat.id ? 'bg-white dark:bg-slate-700 shadow-md scale-105 ring-1 ring-black/5' : 'hover:bg-white/50 dark:hover:bg-slate-800 opacity-70 hover:opacity-100'}`}
              >
                <div className={`w-2 h-2 rounded-full ${stat.bg} shadow-sm shadow-black/10`} />
                <span className={`text-xs font-black ${stat.color === 'green' ? 'text-emerald-600' : stat.color === 'red' ? 'text-rose-600' : stat.color === 'orange' ? 'text-amber-600' : 'text-[#004899]'}`}>
                  {stat.value}
                </span>
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 hidden group-hover:block bg-slate-800 text-white text-[9px] px-2 py-1 rounded-lg shadow-2xl whitespace-nowrap z-50 border border-slate-700">
                  {stat.label} {statusFilter === stat.id ? '(активно)' : ''}
                </div>
              </button>
            ))}
          </div>

          <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-1 hidden sm:block" />

          {/* Controls - More spaced out icons */}
          <div className="flex items-center gap-2 bg-slate-100/50 dark:bg-slate-800/40 p-1 rounded-xl border border-slate-200/60 dark:border-slate-800/60">
            <div className="relative">
              <button 
                onClick={() => setShowSortBy(!showSortMenu)}
                className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg text-slate-500 transition-all"
                title="Сортування"
              >
                <SortAsc className="h-4 w-4" />
              </button>
              <AnimatePresence>
                {showSortMenu && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowSortBy(false)} />
                    <motion.div 
                      initial={{ opacity: 0, y: 5, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 5, scale: 0.95 }}
                      className="absolute left-0 mt-2 w-48 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-100 dark:border-slate-800 py-1.5 z-20 overflow-hidden"
                    >
                      {(Object.keys(sortLabels) as SortOption[]).map((option) => (
                        <button
                          key={option}
                          onClick={() => { setSortBy(option); setShowSortBy(false); }}
                          className={`w-full text-left px-4 py-2 text-[11px] font-bold transition-colors ${sortBy === option ? 'text-[#004899] bg-blue-50 dark:bg-blue-900/20' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                        >
                          {sortLabels[option]}
                        </button>
                      ))}
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>

            <button 
              onClick={() => handleViewChange(viewType === 'grid' ? 'list' : 'grid')}
              className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg text-slate-500 transition-all"
              title={viewType === 'grid' ? 'Список' : 'Плитка'}
            >
              {viewType === 'grid' ? <List className="h-4 w-4" /> : <LayoutGrid className="h-4 w-4" />}
            </button>

            <button 
              onClick={() => {setLoading(true); fetchObjects();}}
              className="p-2 hover:bg-white dark:hover:bg-slate-700 rounded-lg text-[#004899] transition-all group"
              title="Оновити"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
            </button>
          </div>
        </div>
      }
    >
      <div className="flex flex-col gap-6">

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
