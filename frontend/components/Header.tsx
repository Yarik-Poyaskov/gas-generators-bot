'use client';

import { useEffect, useState } from 'react';
import { User, Bell, BellOff, Search, ChevronDown, Sun, Moon, Monitor, Loader2, Menu, Users, Wifi } from 'lucide-react';
import { authService } from '@/lib/auth-service';
import { useTheme } from 'next-themes';
import { registerServiceWorker, subscribeToNotifications, checkSubscriptionStatus, unsubscribeFromNotifications } from '@/lib/notifications';
import api from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';

interface HeaderProps {
  onMenuClick?: () => void;
  centerContent?: React.ReactNode;
  searchQuery?: string;
  setSearchQuery?: (val: string) => void;
}

export default function Header({ onMenuClick, centerContent, searchQuery, setSearchQuery }: HeaderProps) {
  const [userName, setUserName] = useState<string | null>('');
  const [userRole, setUserRole] = useState<string | null>('');
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscribing, setSubscribing] = useState(false);
  
  // Online users logic
  const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
  const [showOnlineList, setShowOnlineList] = useState(false);

  const fetchOnlineUsers = async () => {
    if (userRole !== 'admin') return;
    try {
      const response = await api.get('/online');
      setOnlineUsers(response.data);
    } catch (e) {
      console.error('Failed to fetch online users');
    }
  };

  useEffect(() => {
    setMounted(true);
    const role = authService.getUserRole();
    setUserName(authService.getFullName());
    setUserRole(role);
    
    // Register SW and check subscription
    const initNotifications = async () => {
      await registerServiceWorker();
      const status = await checkSubscriptionStatus();
      setIsSubscribed(status);
    };
    initNotifications();

    // Initial fetch
    if (role === 'admin') {
      fetchOnlineUsers();
      const interval = setInterval(fetchOnlineUsers, 30000); // Every 30s
      return () => clearInterval(interval);
    }
  }, [userRole]);

  const handleSubscribe = async () => {
    setSubscribing(true);
    const success = await subscribeToNotifications();
    if (success) setIsSubscribed(true);
    setSubscribing(false);
  };

  const handleUnsubscribe = async () => {
    setSubscribing(true);
    const success = await unsubscribeFromNotifications();
    if (success) setIsSubscribed(false);
    setSubscribing(false);
  };

  if (!mounted) {
    return (
      <header className="sticky top-0 z-30 h-20 w-full bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between">
        <div className="flex-1 max-w-xl"></div>
      </header>
    );
  }

  return (
    <header className="sticky top-4 z-30 h-18 mx-4 lg:mx-8 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-[1.5rem] px-4 lg:px-6 flex items-center justify-between transition-all shadow-lg shadow-black/5">
      <div className="flex items-center gap-6 flex-1">
        {/* Mobile Menu Trigger */}
        <button 
          onClick={onMenuClick}
          className="p-2 bg-slate-100 dark:bg-slate-900 rounded-xl text-slate-600 dark:text-slate-400 lg:hidden hover:bg-slate-200 transition-colors"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="relative group w-full max-w-[200px] hidden sm:block">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400 group-focus-within:text-[#004899] transition-colors" />
          </div>
          <input
            type="text"
            placeholder="Пошук..."
            value={searchQuery}
            onChange={(e) => setSearchQuery?.(e.target.value)}
            className="block w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-900 border-2 border-transparent focus:border-[#004899]/20 focus:bg-white dark:focus:bg-slate-950 rounded-xl transition-all text-xs font-bold text-slate-900 dark:text-white outline-none"
          />
        </div>

        <div className="flex items-center gap-6">
          {centerContent}
        </div>
      </div>

      <div className="flex items-center gap-3 ml-4">
        {/* Admin Online List */}
        {userRole === 'admin' && (
          <div className="relative">
            <button 
              onClick={() => setShowOnlineList(!showOnlineList)}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${onlineUsers.length > 0 ? 'bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}
              title="Користувачі на сайті"
            >
              <div className="relative">
                <Wifi className="h-4 w-4" />
                {onlineUsers.length > 0 && <span className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-500 rounded-full animate-pulse border border-white dark:border-slate-900" />}
              </div>
              <span className="text-xs font-black">{onlineUsers.length}</span>
            </button>
            
            <AnimatePresence>
              {showOnlineList && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowOnlineList(false)} />
                  <motion.div 
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-3 w-64 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-100 dark:border-slate-800 py-3 z-20 overflow-hidden"
                  >
                    <div className="px-4 pb-2 mb-2 border-b border-slate-50 dark:border-slate-800">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Онлайн зараз</p>
                    </div>
                    <div className="max-h-60 overflow-y-auto px-2 space-y-1">
                      {onlineUsers.length > 0 ? onlineUsers.map((name, i) => (
                        <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                          <span className="text-[11px] font-bold text-slate-700 dark:text-slate-200">{name}</span>
                        </div>
                      )) : (
                        <p className="text-[11px] text-slate-400 italic px-3 py-2">Нікого немає</p>
                      )}
                    </div>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Theme Switcher */}
        <div className="hidden md:flex items-center bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800 scale-90">
          <button onClick={() => setTheme('light')} className={`p-2 rounded-lg transition-all ${theme === 'light' ? 'bg-white text-amber-500 shadow-sm' : 'text-slate-400'}`} title="Світла"><Sun className="h-4 w-4" /></button>
          <button onClick={() => setTheme('system')} className={`p-2 rounded-lg transition-all ${theme === 'system' ? 'bg-white dark:bg-slate-800 text-blue-500 shadow-sm' : 'text-slate-400'}`} title="Система"><Monitor className="h-4 w-4" /></button>
          <button onClick={() => setTheme('dark')} className={`p-2 rounded-lg transition-all ${theme === 'dark' ? 'bg-white dark:bg-slate-800 text-indigo-400 shadow-sm' : 'text-slate-400'}`} title="Темна"><Moon className="h-4 w-4" /></button>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={isSubscribed ? handleUnsubscribe : handleSubscribe}
            disabled={subscribing}
            className={`p-2.5 rounded-2xl transition-all relative group ${isSubscribed ? 'text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/20' : 'text-slate-500 hover:text-[#004899] hover:bg-blue-50 dark:hover:bg-slate-900'}`}
          >
            {subscribing ? <Loader2 className="h-5.5 w-5.5 animate-spin" /> : <Bell className="h-5.5 w-5.5" />}
            {isSubscribed && <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-white dark:border-slate-950"></span>}
          </button>
        </div>
        
        <div className="flex items-center gap-4 pl-6 border-l border-slate-200 dark:border-slate-800">
          <div className="flex flex-col items-end hidden md:flex">
            <p className="text-sm font-bold text-slate-900 dark:text-white leading-tight">{userName || 'Користувач'}</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#f6c400]" />
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{userRole || 'Гість'}</p>
            </div>
          </div>
          
          <button onClick={() => authService.logout()} className="flex items-center gap-2 group hover:opacity-80 transition-opacity" title="Вийти">
            <div className="h-11 w-11 rounded-2xl bg-[#004899] p-[2px] shadow-lg shadow-blue-500/20">
              <div className="h-full w-full rounded-[14px] bg-white dark:bg-slate-900 flex items-center justify-center overflow-hidden">
                <User className="h-6 w-6 text-[#004899]" />
              </div>
            </div>
            <ChevronDown className="h-4 w-4 text-slate-400" />
          </button>
        </div>
      </div>
    </header>
  );
}
