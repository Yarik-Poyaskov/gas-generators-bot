'use client';

import { useEffect, useState, useMemo, useRef } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import GPUCardCompact from '@/components/GPUCardCompact';
import { ObjectInfo } from '@/types';
import api from '@/lib/api';
import { authService } from '@/lib/auth-service';
import { LayoutGrid, List, RefreshCw, Loader2, Search as SearchIcon, SortAsc, ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type SortOption = 'alphabetical' | 'status' | 'power' | 'last_report';

export default function CompactTestDashboard() {
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

  // Logic for "Smart Delay" (Freezing position during status change)
  const [frozenIds, setFrozenIds] = useState<Record<number, ObjectInfo>>({});
  const lastActivityRef = useRef<number>(Date.now());
  const wsRef = useRef<WebSocket | null>(null);

  const fetchObjects = async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      const response = await api.get('/data/objects');
      const newObjects = response.data;
      
      setObjects(newObjects);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch objects:', error);
    } finally {
      setLoading(false);
    }
  };

  // WebSocket Connection with Reconnect logic
  const connectWebSocket = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    let wsUrl = '';
    if (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL.startsWith('ws')) {
      wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}?token=${token}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/api/ws/status?token=${token}`;
    }

    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'new_report') {
        const objId = message.data.obj_id;
        
        // Find the current object data to "freeze" its position
        const currentObj = objects.find(o => o.id === objId);
        if (currentObj) {
          setFrozenIds(prev => ({ ...prev, [objId]: { ...currentObj } }));
          
          // Unfreeze after 10 seconds (move to new position)
          setTimeout(() => {
            setFrozenIds(prev => {
              const next = { ...prev };
              delete next[objId];
              return next;
            });
          }, 10000);
        }

        fetchObjects(true);
        setNewReportId(objId);
        // Flashing for 15 seconds total (10 before move, 5 after)
        setTimeout(() => setNewReportId(null), 15000);
      }
    };

    socket.onclose = () => {
      setTimeout(connectWebSocket, 5000);
    };
  };

  useEffect(() => {
    const savedView = localStorage.getItem('dashboard_view_type');
    if (savedView === 'grid' || savedView === 'list') {
      setViewType(savedView);
    }
    
    if (!localStorage.getItem('access_token')) {
      window.location.href = '/login';
      return;
    }

    fetchObjects();
    connectWebSocket();

    const handleActivity = () => {
      const now = Date.now();
      if (now - lastActivityRef.current > 10 * 60 * 1000) {
        lastActivityRef.current = now;
        authService.refreshToken();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchObjects(true);
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          connectWebSocket();
        }
      }
    };

    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleVisibilityChange);

    return () => {
      if (wsRef.current) wsRef.current.close();
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleVisibilityChange);
    };
  }, [objects.length === 0]);

  const sortedObjects = useMemo(() => {
    let baseList = [...objects];
    
    if (statusFilter === 'stable') {
      baseList = baseList.filter(o => (o.gpu_status || '').toLowerCase().includes('стабільна'));
    } else if (statusFilter === 'stopped') {
      baseList = baseList.filter(o => (o.gpu_status || '').toLowerCase().includes('не працює'));
    } else if (statusFilter === 'emergency') {
      baseList = baseList.filter(o => (o.gpu_status || '').toLowerCase().includes('аварі') || (o.gpu_status || '').toLowerCase().includes('не готова'));
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      baseList = baseList.filter(o => 
        o.name.toLowerCase().includes(q) || 
        (o.short_name || '').toLowerCase().includes(q)
      );
    }

    const sortMultiplier = sortOrder === 'asc' ? 1 : -1;

    baseList.sort((a, b) => {
      const sortA = frozenIds[a.id] || a;
      const sortB = frozenIds[b.id] || b;

      let comparison = 0;
      switch (sortBy) {
        case 'alphabetical':
          comparison = sortA.name.localeCompare(sortB.name);
          break;
        case 'status':
          const getStatusWeight = (status: string | null = '') => {
            if (!status || status.toLowerCase().includes('очікування')) return 10;
            const s = status.toLowerCase();
            if (s.includes('аварі') || s.includes('не готова')) return 3;
            if (s.includes('не працює')) return 2;
            if (s.includes('стабільна')) return 0;
            return 4;
          };
          comparison = getStatusWeight(sortA.gpu_status) - getStatusWeight(sortB.gpu_status);
          break;
        case 'power':
          comparison = Number(sortB.load_power_percent || 0) - Number(sortA.load_power_percent || 0);
          break;
      }
      return comparison * sortMultiplier;
    });

    return baseList;
  }, [objects, sortBy, sortOrder, searchQuery, statusFilter, frozenIds]);

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
                Компактний Тест
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
            </div>
            <p className="text-slate-500 font-bold mt-6 animate-pulse uppercase tracking-[0.2em] text-[10px]">Завантаження даних...</p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 [.sidebar-collapsed_&]:lg:grid-cols-4 [.sidebar-collapsed_&]:xl:grid-cols-5 [.sidebar-collapsed_&]:2xl:grid-cols-6 gap-6">
            {sortedObjects.map((obj) => (
              <GPUCardCompact 
                key={obj.id} 
                data={obj} 
                isNew={newReportId === obj.id}
              />
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
