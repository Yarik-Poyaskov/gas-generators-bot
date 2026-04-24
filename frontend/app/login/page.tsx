'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/lib/auth-service';
import { Shield, Smartphone, Key, AlertCircle, Loader2, ArrowRight, Building2, Lock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function LoginPage() {
  const [identifier, setIdentifier] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState(1); // 1: identifier, 2: code
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim()) return;
    
    setLoading(true);
    setError('');
    try {
      await authService.requestCode(identifier);
      setStep(2);
    } catch (err: any) {
      console.error('Login error:', err);
      const msg = err.response?.data?.detail || 'Сервіс тимчасово недоступний. Перевірте роботу бота.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim() || code.length !== 6) return;
    
    setLoading(true);
    setError('');
    try {
      await authService.verifyCode(identifier, code);
      router.push('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Невірний або прострочений код.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background visual effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#004899] rounded-full blur-[150px] opacity-20 animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#f6c400] rounded-full blur-[180px] opacity-10" />
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10 pointer-events-none" />

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full z-10"
      >
        {/* Branding Header */}
        <div className="flex flex-col items-center mb-12">
          <motion.div 
            initial={{ y: -20 }}
            animate={{ y: 0 }}
            className="flex items-center gap-4 mb-6"
          >
            <div className="bg-gradient-to-br from-[#004899] to-[#003675] p-3.5 rounded-2xl shadow-2xl border border-white/10">
              <Building2 className="text-white w-9 h-9" strokeWidth={2.2} />
            </div>
            <div className="h-12 w-[1px] bg-white/20" />
            <div className="flex flex-col">
              <span className="text-white font-black text-3xl tracking-tighter leading-none">ЕПІЦЕНТР К</span>
              <span className="text-blue-400 text-[10px] font-black uppercase tracking-[0.3em] mt-1.5">Energy Portal</span>
            </div>
          </motion.div>
          
          <h1 className="text-4xl font-black text-white text-center tracking-tight mb-3">Авторизація</h1>
          <p className="text-slate-400 text-center font-medium opacity-80 flex items-center gap-2">
            <Lock className="w-4 h-4 text-[#f6c400]" /> Безпечний вхід через Telegram
          </p>
        </div>

        {/* Auth Card */}
        <div className="bg-white/10 backdrop-blur-2xl rounded-[3rem] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)] p-10 border border-white/20 relative overflow-hidden group">
          {/* Subtle light effect on hover */}
          <div className="absolute -inset-x-20 -inset-y-20 bg-gradient-to-tr from-[#004899]/0 via-[#004899]/5 to-[#f6c400]/0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

          <AnimatePresence mode="wait">
            {error && (
              <motion.div 
                initial={{ opacity: 0, height: 0, y: -10 }}
                animate={{ opacity: 1, height: 'auto', y: 0 }}
                exit={{ opacity: 0, height: 0, y: -10 }}
                className="mb-8 overflow-hidden"
              >
                <div className="p-5 bg-red-500/10 border border-red-500/30 rounded-[1.5rem] flex items-start gap-4 text-red-400 text-sm font-bold shadow-lg shadow-red-900/10">
                  <AlertCircle className="w-5 h-5 shrink-0" />
                  <p>{error}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {step === 1 ? (
              <motion.form 
                key="step1"
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 30 }}
                onSubmit={handleRequestCode} 
                className="space-y-8"
              >
                <div className="space-y-3">
                  <label htmlFor="identifier" className="block text-xs font-black text-blue-300 uppercase tracking-widest ml-1 opacity-70">
                    Номер телефону або ID
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#004899]">
                      <Smartphone className="h-6 w-6 transition-colors" />
                    </div>
                    <input
                      id="identifier"
                      type="text"
                      placeholder="380991234567 або !12345"
                      className="block w-full pl-14 pr-6 py-5 bg-slate-900/40 border-2 border-white/5 rounded-[1.5rem] focus:ring-0 focus:border-[#004899] focus:bg-slate-900/60 outline-none transition-all text-white font-bold text-lg placeholder:text-slate-600 shadow-inner"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  <p className="text-[10px] text-slate-500 font-bold ml-1 italic">
                    * Почніть з ! якщо використовуєте Telegram ID
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={loading || !identifier}
                  className="w-full h-16 bg-gradient-to-r from-[#004899] to-[#003675] hover:from-[#0052ad] hover:to-[#004899] disabled:from-slate-800 disabled:to-slate-900 text-white font-black py-4 px-6 rounded-[1.5rem] shadow-[0_15px_30px_-5px_rgba(0,72,153,0.3)] active:scale-[0.97] transition-all flex items-center justify-center gap-3 group relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                  {loading ? (
                    <Loader2 className="w-7 h-7 animate-spin" />
                  ) : (
                    <>
                      <span className="relative text-lg uppercase tracking-wider">Отримати код</span>
                      <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform relative" strokeWidth={3} />
                    </>
                  )}
                </button>
              </motion.form>
            ) : (
              <motion.form 
                key="step2"
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 30 }}
                onSubmit={handleVerifyCode} 
                className="space-y-8"
              >
                <div className="bg-[#004899]/20 p-6 rounded-[1.5rem] border border-[#004899]/30 flex gap-4">
                  <div className="w-10 h-10 bg-[#004899] rounded-xl flex items-center justify-center shrink-0">
                    <Shield className="w-6 h-6 text-white" />
                  </div>
                  <p className="text-blue-100 text-sm font-semibold leading-relaxed pt-0.5">
                    Ми надіслали <b>6-значний код</b> у ваш Telegram-бот. Будь ласка, введіть його нижче.
                  </p>
                </div>

                <div className="space-y-3">
                  <label htmlFor="code" className="block text-xs font-black text-blue-300 uppercase tracking-widest ml-1 opacity-70">
                    Код підтвердження
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                      <Key className="h-6 w-6 text-slate-400" />
                    </div>
                    <input
                      id="code"
                      type="text"
                      maxLength={6}
                      placeholder="0 0 0 0 0 0"
                      className="block w-full pl-14 pr-6 py-5 bg-slate-900/40 border-2 border-white/5 rounded-[1.5rem] focus:ring-0 focus:border-[#004899] focus:bg-slate-900/60 outline-none transition-all text-white tracking-[1em] text-center font-black text-3xl placeholder:text-slate-700 shadow-inner"
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="flex gap-4 pt-2">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="flex-1 bg-white/5 hover:bg-white/10 text-white font-bold py-5 px-4 rounded-[1.5rem] transition-all active:scale-[0.97] border border-white/10 text-sm uppercase tracking-widest"
                    disabled={loading}
                  >
                    Назад
                  </button>
                  <button
                    type="submit"
                    disabled={loading || code.length !== 6}
                    className="flex-[2] bg-gradient-to-r from-[#004899] to-[#003675] text-white font-black py-5 px-6 rounded-[1.5rem] shadow-xl active:scale-[0.97] transition-all flex items-center justify-center gap-2 group text-sm uppercase tracking-widest overflow-hidden relative"
                  >
                    <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                    {loading ? <Loader2 className="w-7 h-7 animate-spin" /> : <span className="relative">Увійти</span>}
                  </button>
                </div>
              </motion.form>
            )}
          </AnimatePresence>
        </div>

        {/* Brand Footer */}
        <div className="mt-16 text-center space-y-6">
          <p className="text-white/30 text-[10px] font-black uppercase tracking-[0.4em]">
            © {new Date().getFullYear()} ТОВ "Епіцентр К" · ENERGY MONITORING SYSTEM
          </p>
          <div className="flex justify-center gap-8 items-center">
            <div className="w-24 h-[1px] bg-gradient-to-r from-transparent to-white/10" />
            <div className="flex gap-3">
              <div className="w-2 h-2 rounded-full bg-[#f6c400] shadow-[0_0_10px_#f6c400] animate-pulse" />
              <div className="w-2 h-2 rounded-full bg-white/10" />
              <div className="w-2 h-2 rounded-full bg-white/10" />
            </div>
            <div className="w-24 h-[1px] bg-gradient-to-l from-transparent to-white/10" />
          </div>
        </div>
      </motion.div>
    </div>
  );
}
