'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/lib/auth-service';
import Sidebar from '@/components/Sidebar';
import Header from '@/components/Header';
import { Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [loading, setLoading] = useState(true);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!authService.isAuthenticated()) {
      router.push('/login');
    } else {
      setLoading(false);
      const saved = localStorage.getItem('sidebar_collapsed');
      if (saved === 'true') setIsCollapsed(true);
    }
  }, [router]);

  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem('sidebar_collapsed', newState.toString());
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 text-[#004899] animate-spin mb-4" />
        <p className="text-slate-500 font-medium animate-pulse">Перевірка авторизації...</p>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-[#f1f5f9] dark:bg-slate-950 transition-colors duration-300 ${isCollapsed ? 'sidebar-collapsed' : 'sidebar-expanded'}`}>
      <Sidebar isCollapsed={isCollapsed} onToggle={toggleSidebar} />
      <div className={`${isCollapsed ? 'ml-24' : 'ml-72'} transition-all duration-300 ease-in-out`}>
        <Header />
        <motion.main 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-8 max-w-[2000px] mx-auto"
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
