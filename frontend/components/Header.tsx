'use client';

import { useEffect, useState } from 'react';
import { User, Bell, BellOff, Search, Command, ChevronDown, Sun, Moon, Monitor, Loader2 } from 'lucide-react';
import { authService } from '@/lib/auth-service';
import { useTheme } from 'next-themes';
import { registerServiceWorker, subscribeToNotifications, checkSubscriptionStatus } from '@/lib/notifications';

export default function Header() {
  const [userName, setUserName] = useState<string | null>('');
  const [userRole, setUserRole] = useState<string | null>('');
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    setMounted(true);
    setUserName(authService.getFullName());
    setUserRole(authService.getUserRole());
    
    // Register SW and check subscription
    const initNotifications = async () => {
      await registerServiceWorker();
      const status = await checkSubscriptionStatus();
      setIsSubscribed(status);
    };
    initNotifications();
  }, []);

  const handleSubscribe = async () => {
    setSubscribing(true);
    const success = await subscribeToNotifications();
    if (success) setIsSubscribed(true);
    setSubscribing(false);
  };

  // Avoid hydration mismatch by not rendering anything theme-specific until mounted
  if (!mounted) {
    return (
      <header className="sticky top-0 z-30 h-20 w-full bg-white dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between">
        <div className="flex-1 max-w-xl"></div>
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-30 h-20 w-full bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between transition-colors">
      <div className="flex-1 max-w-xl">
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-4.5 w-4.5 text-slate-400 group-focus-within:text-[#004899] transition-colors" />
          </div>
          <input
            type="text"
            placeholder="Пошук звітів, об'єктів або команд..."
            className="block w-full pl-11 pr-12 py-3 bg-slate-100 dark:bg-slate-900 border-2 border-transparent focus:border-[#004899]/20 focus:bg-white dark:focus:bg-slate-950 rounded-2xl transition-all text-sm font-medium text-slate-900 dark:text-white outline-none"
          />
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <kbd className="hidden sm:flex items-center gap-1 px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-[10px] text-slate-400 font-bold">
              <Command className="w-3 h-3" /> K
            </kbd>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-6">
        {/* Theme Switcher */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800">
          <button 
            onClick={() => setTheme('light')}
            className={`p-2 rounded-lg transition-all ${theme === 'light' ? 'bg-white text-amber-500 shadow-sm' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
            title="Світла тема"
          >
            <Sun className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setTheme('system')}
            className={`p-2 rounded-lg transition-all ${theme === 'system' ? 'bg-white dark:bg-slate-800 text-blue-500 shadow-sm' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
            title="Системна тема"
          >
            <Monitor className="h-4 w-4" />
          </button>
          <button 
            onClick={() => setTheme('dark')}
            className={`p-2 rounded-lg transition-all ${theme === 'dark' ? 'bg-white dark:bg-slate-800 text-indigo-400 shadow-sm' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
            title="Темна тема"
          >
            <Moon className="h-4 w-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={!isSubscribed ? handleSubscribe : undefined}
            disabled={subscribing}
            className={`p-2.5 rounded-2xl transition-all relative group ${isSubscribed ? 'text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/20' : 'text-slate-500 hover:text-[#004899] hover:bg-blue-50 dark:hover:bg-slate-900'}`}
            title={isSubscribed ? 'Сповіщення увімкнено' : 'Увімкнути сповіщення'}
          >
            {subscribing ? (
              <Loader2 className="h-5.5 w-5.5 animate-spin" />
            ) : isSubscribed ? (
              <Bell className="h-5.5 w-5.5" />
            ) : (
              <BellOff className="h-5.5 w-5.5" />
            )}
            {isSubscribed && (
              <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-white dark:border-slate-950 ring-2 ring-emerald-500/20"></span>
            )}
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
          
          <button 
            onClick={() => authService.logout()}
            className="flex items-center gap-2 group hover:opacity-80 transition-opacity"
            title="Вийти з системи"
          >
            <div className="h-11 w-11 rounded-2xl bg-[#004899] p-[2px] shadow-lg shadow-blue-500/20 transition-transform group-hover:scale-105 active:scale-95">
              <div className="h-full w-full rounded-[14px] bg-white dark:bg-slate-900 flex items-center justify-center overflow-hidden">
                <User className="h-6 w-6 text-[#004899]" />
              </div>
            </div>
            <div className="flex flex-col items-start">
              <ChevronDown className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors" />
              <span className="text-[8px] font-black text-red-500 uppercase hidden group-hover:block leading-none mt-1">Вихід</span>
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}
