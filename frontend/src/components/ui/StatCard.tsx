import React from 'react';
import { Info } from 'lucide-react';
import { Card } from './Card';
import { Skeleton } from './Skeleton';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: string;
  trendTone?: 'positive' | 'negative' | 'neutral';
  tooltip?: string;
  isLoading?: boolean;
}

const TREND_TONE_CLASSES: Record<NonNullable<StatCardProps['trendTone']>, string> = {
  positive: 'bg-emerald-950/60 border-emerald-500/30 text-spotify-green',
  negative: 'bg-rose-950/60 border-rose-500/30 text-rose-400',
  neutral: 'bg-slate-800/70 border-slate-700 text-slate-300',
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendTone = 'positive',
  tooltip,
  isLoading = false,
}) => {
  return (
    <Card
      variant="default"
      padding="sm"
      interactive
      className="sm:p-5 group hover:-translate-y-0.5 min-w-0 flex flex-col justify-between"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] sm:text-xs font-semibold text-text-muted uppercase tracking-wider leading-snug">
            {title}
          </span>
          {tooltip && (
            <span
              className="text-text-muted hover:text-slate-200 transition-colors cursor-help shrink-0"
              title={tooltip}
              aria-label={tooltip}
            >
              <Info className="w-3.5 h-3.5" />
            </span>
          )}
        </div>
        <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-obsidian-bg border border-obsidian-border group-hover:border-spotify-green/35 flex items-center justify-center text-spotify-green transition-all shrink-0">
          {icon}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2 py-1" aria-busy="true">
          <Skeleton className="h-7 sm:h-8 w-24" />
          <Skeleton className="h-3.5 w-32 opacity-75" />
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-baseline gap-2 min-w-0">
            <span className="text-xl sm:text-3xl font-extrabold text-white tracking-tight truncate">
              {value}
            </span>
            {trend && (
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${TREND_TONE_CLASSES[trendTone]}`}
              >
                {trend}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] sm:text-xs text-text-muted mt-1 font-normal truncate" title={subtitle}>
              {subtitle}
            </p>
          )}
        </>
      )}
    </Card>
  );
};
