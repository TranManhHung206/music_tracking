import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
}) => {
  return (
    <div className="bg-[#131B2E] border border-[#1E293B] hover:border-[#1DB954]/40 rounded-2xl p-5 shadow-lg transition-all duration-300 hover:translate-y-[-2px] group">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        <div className="w-9 h-9 rounded-xl bg-[#0B0F17] border border-[#1E293B] group-hover:border-[#1DB954]/30 flex items-center justify-center text-[#1DB954] transition-all">
          {icon}
        </div>
      </div>
      <div className="flex items-baseline space-x-2">
        <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
          {value}
        </span>
        {trend && (
          <span className="text-xs font-semibold text-emerald-400">
            {trend}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="text-xs text-slate-500 mt-1 font-normal">
          {subtitle}
        </p>
      )}
    </div>
  );
};
