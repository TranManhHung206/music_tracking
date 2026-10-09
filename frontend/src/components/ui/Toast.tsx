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
    <div className="fixed bottom-6 right-6 z-50 flex flex-col space-y-3 max-w-md w-full px-4 sm:px-0">
      {toasts.map((toast) => {
        let borderClass = 'border-slate-700';
        let bgClass = 'bg-[#131B2E]';
        let textClass = 'text-slate-200';
        let Icon = Info;

        if (toast.type === 'success') {
          borderClass = 'border-[#1DB954]/50';
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
            className={`flex items-start justify-between p-4 rounded-xl border ${borderClass} ${bgClass} shadow-xl backdrop-blur-md transition-all duration-300 animate-in fade-in slide-in-from-bottom-2`}
          >
            <div className="flex items-start space-x-3">
              <Icon className={`w-5 h-5 mt-0.5 shrink-0 ${textClass}`} />
              <p className="text-xs sm:text-sm font-medium text-slate-200 leading-relaxed">
                {toast.message}
              </p>
            </div>
            <button
              onClick={() => onDismiss(toast.id)}
              className="ml-3 text-slate-400 hover:text-white transition-colors cursor-pointer shrink-0"
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
