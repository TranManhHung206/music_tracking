import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="fixed bottom-4 sm:bottom-6 left-4 right-4 sm:left-auto sm:right-6 pb-[env(safe-area-inset-bottom)] z-50 flex flex-col gap-3 sm:max-w-md sm:w-full pointer-events-none"
    >
      {toasts.map((toast) => {
        let borderClass = 'border-slate-700';
        let bgClass = 'bg-obsidian-card';
        let textClass = 'text-slate-200';
        let Icon = Info;

        if (toast.type === 'success') {
          borderClass = 'border-spotify-green/50';
          bgClass = 'bg-[#0B1A14]';
          textClass = 'text-emerald-300';
          Icon = CheckCircle2;
        } else if (toast.type === 'error') {
          borderClass = 'border-rose-500/50';
          bgClass = 'bg-[#1F0D12]';
          textClass = 'text-rose-300';
          Icon = AlertCircle;
        } else if (toast.type === 'warning') {
          borderClass = 'border-amber-500/50';
          bgClass = 'bg-[#1F180B]';
          textClass = 'text-amber-300';
          Icon = AlertTriangle;
        }

        return (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto flex items-start justify-between p-3.5 sm:p-4 rounded-xl border ${borderClass} ${bgClass} shadow-xl backdrop-blur-md transition-all duration-300 animate-slide-up`}
          >
            <div className="flex items-start gap-3 min-w-0">
              <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${textClass}`} />
              <p className="text-xs sm:text-sm font-medium text-slate-200 leading-relaxed break-words">
                {toast.message}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              aria-label="Đóng thông báo"
              className="ml-3 min-w-[28px] min-h-[28px] rounded-lg flex items-center justify-center text-slate-400 hover:text-white transition-colors cursor-pointer shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              title="Đóng"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
