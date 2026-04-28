'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  ClipboardList,
  Zap,
  Calendar,
  Settings,
  LogOut,
  Building2,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';import { authService } from '@/lib/auth-service';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { motion } from 'framer-motion';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { name: 'Дашборд', href: '/', icon: LayoutDashboard },
  { name: 'Звіт (чергові)', href: '/reports/summary-shifts', icon: ClipboardList },
  { name: 'Звіт за сьогодні', href: '/reports/summary-power', icon: Zap },
  { name: 'Графіки (Трейдер)', href: '/trader', icon: Calendar },
  { name: 'Налаштування', href: '/settings', icon: Settings },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    setUserRole(authService.getUserRole());
  }, []);

  const filteredNavItems = navItems.filter(item => {
    // Basic rules:
    // Regular users can only see Dashboard.
    // Traders and Admins see everything.
    if (userRole === 'user') {
      return item.href === '/';
    }
    return true;
  });

  return (
    <>
      {/* Mobile Overlay - blurred background when sidebar is open on mobile */}
      {!isCollapsed && (
        <div 
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300"
          onClick={onToggle}
        />
      )}

      <aside className={cn(
        "fixed left-0 top-0 z-50 h-screen bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 transition-all duration-300 ease-in-out shadow-xl shadow-slate-200/50 dark:shadow-none",
        isCollapsed ? "w-24 -translate-x-full lg:translate-x-0 lg:w-24" : "w-72 translate-x-0"
      )}>
        <div className="flex h-full flex-col relative">
          {/* Desktop Collapse Toggle Button - hidden on mobile */}
          <button 
            onClick={onToggle}
            className="absolute -right-3 top-10 z-50 h-6 w-6 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hidden lg:flex items-center justify-center shadow-md hover:text-[#004899] transition-colors"
          >
            {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>

          {/* Close button for mobile - visible only when expanded on mobile */}
          <button 
            onClick={onToggle}
            className="absolute right-4 top-6 z-50 p-2 text-slate-400 hover:text-slate-600 lg:hidden"
          >
            <ChevronLeft className="h-6 w-6" />
          </button>

          {/* Brand Header */}
          <div className={cn("transition-all duration-300", isCollapsed ? "p-4" : "p-6")}>
            <div className="flex items-center gap-3">
              <div className={cn(
                "flex items-center justify-center rounded-2xl bg-[#004899] shadow-lg shadow-blue-500/30 shrink-0 transition-all",
                isCollapsed ? "h-12 w-12" : "h-12 w-12"
              )}>
                <Building2 className="text-white w-7 h-7" strokeWidth={2.5} />
              </div>
              {!isCollapsed && (
                <motion.div 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex flex-col overflow-hidden"
                >
                  <span className="text-xl font-black text-slate-900 dark:text-white leading-none tracking-tight whitespace-nowrap">ЕПІЦЕНТР К</span>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Energy Portal</span>
                </motion.div>
              )}
            </div>
          </div>
          
          {/* Navigation */}
          <nav className="flex-1 px-4 space-y-1.5 font-medium overflow-y-auto custom-scrollbar overflow-x-hidden">
            {!isCollapsed && (
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-4 mb-2 mt-4">Основне меню</div>
            )}
            {filteredNavItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={isCollapsed ? item.name : ""}
                  className={cn(
                    "flex items-center rounded-2xl transition-all duration-200 group relative",
                    isCollapsed ? "justify-center px-0 py-3.5" : "justify-between px-4 py-3.5",
                    isActive 
                      ? "bg-[#004899] text-white shadow-lg shadow-blue-500/20" 
                      : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900 hover:text-[#004899] dark:hover:text-white"
                  )}
                >
                  <div className="flex items-center">
                    <item.icon className={cn(
                      "h-5 w-5 transition-transform duration-200 group-hover:scale-110 shrink-0",
                      isCollapsed ? "" : "mr-3.5",
                      isActive ? "text-white" : "text-slate-400 group-hover:text-[#004899]"
                    )} />
                    {!isCollapsed && (
                      <span className="text-[15px] font-semibold whitespace-nowrap">{item.name}</span>
                    )}
                  </div>
                  {!isCollapsed && isActive && (
                    <ChevronRight className="h-4 w-4 text-white/70" />
                  )}
                  {isCollapsed && isActive && (
                    <div className="absolute left-0 w-1 h-6 bg-[#004899] rounded-r-full" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Logout */}
          <div className={cn("p-4 mt-auto border-t border-slate-100 dark:border-slate-800 transition-all", isCollapsed ? "px-2" : "p-4")}>
            <button
              onClick={() => authService.logout()}
              title="Вийти з системи"
              className={cn(
                "flex items-center justify-center gap-2 rounded-2xl bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-all font-bold group overflow-hidden",
                isCollapsed ? "w-12 h-12 mx-auto" : "w-full px-4 py-3.5"
              )}
            >
              <LogOut className="h-5 w-5 transition-transform group-hover:-translate-x-1 shrink-0" />
              {!isCollapsed && <span>Вихід</span>}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
