import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, Zap, Calendar } from 'lucide-react';
import type { WeeklyComparisonData, DayComparison } from '../../types/analytics';

interface WeeklyComparisonChartProps {
  data: WeeklyComparisonData;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: DayComparison;
  }>;
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const dayData = payload[0].payload;
    const diff = dayData.diff;

    return (
      <div className="bg-[#0B0F17]/95 border border-[#1E293B] rounded-xl p-3 shadow-2xl backdrop-blur-md min-w-[180px]">
        <p className="text-xs font-bold text-white mb-2 flex items-center justify-between">
          <span>{label}</span>
          <span className="text-[11px] text-slate-400 font-normal">
            {dayData.day_name_en}
          </span>
        </p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center space-x-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#1DB954]" />
              <span>Tuần này:</span>
            </span>
            <span className="font-mono font-bold text-white">
              {dayData.current_week_plays} lượt
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center space-x-1.5 text-slate-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#6366F1]" />
              <span>Tuần trước:</span>
            </span>
            <span className="font-mono text-slate-300">
              {dayData.previous_week_plays} lượt
            </span>
          </div>
          <div className="pt-1.5 border-t border-slate-800 flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Chênh lệch:</span>
            <span
              className={`font-mono font-bold ${
                diff > 0
                  ? 'text-[#1DB954]'
                  : diff < 0
                  ? 'text-rose-400'
                  : 'text-slate-400'
              }`}
            >
              {diff > 0 ? `+${diff}` : diff} lượt
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export const WeeklyComparisonChart: React.FC<WeeklyComparisonChartProps> = ({ data }) => {
  const summary = data?.summary || {
    total_current_week: 0,
    total_previous_week: 0,
    growth_percentage: 0,
    peak_day_current: 'Thứ 2',
    peak_plays_current: 0,
  };

  const isGrowth = summary.growth_percentage > 0;
  const isDecline = summary.growth_percentage < 0;

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      {/* Header & Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center space-x-2">
            <Calendar className="w-5 h-5 text-[#1DB954]" />
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
              So Sánh Lượt Nghe Theo Tuần
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            {data.current_week_label || 'Tuần này'} so với {data.previous_week_label || 'Tuần trước'}
          </p>
        </div>

        {/* Quick Stat Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Badge 1: Tổng lượt tuần này */}
          <div className="px-3 py-1.5 rounded-xl bg-[#0B0F17]/70 border border-[#1E293B] flex items-center space-x-2">
            <span className="text-[11px] text-slate-400">Tuần này:</span>
            <span className="text-xs font-mono font-bold text-white">
              {summary.total_current_week}
            </span>
          </div>

          {/* Badge 2: Tăng trưởng */}
          <div
            className={`px-3 py-1.5 rounded-xl border flex items-center space-x-1.5 ${
              isGrowth
                ? 'bg-emerald-950/40 border-emerald-500/30 text-[#1DB954]'
                : isDecline
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-400'
                : 'bg-slate-900 border-slate-700 text-slate-400'
            }`}
          >
            {isGrowth ? (
              <TrendingUp className="w-3.5 h-3.5" />
            ) : isDecline ? (
              <TrendingDown className="w-3.5 h-3.5" />
            ) : (
              <Minus className="w-3.5 h-3.5" />
            )}
            <span className="text-xs font-mono font-bold">
              {summary.growth_percentage > 0 ? `+${summary.growth_percentage}%` : `${summary.growth_percentage}%`}
            </span>
          </div>

          {/* Badge 3: Ngày cao điểm */}
          {summary.peak_plays_current > 0 && (
            <div className="px-3 py-1.5 rounded-xl bg-[#0B0F17]/70 border border-[#1E293B] flex items-center space-x-1.5 text-amber-400">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs text-slate-300">
                Cao điểm: <strong className="text-white">{summary.peak_day_current}</strong> ({summary.peak_plays_current} lượt)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chart Canvas */}
      {(!data.days || data.days.length === 0 || (summary.total_current_week === 0 && summary.total_previous_week === 0)) ? (
        <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs bg-[#0B0F17]/30 rounded-xl border border-[#1E293B]/40">
          <p>Chưa có dữ liệu lượt nghe cho các ngày trong tuần này.</p>
        </div>
      ) : (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.days}
              margin={{ top: 10, right: 15, left: -20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis
                dataKey="day_name"
                stroke="#64748B"
                tick={{ fill: '#94A3B8', fontSize: 12 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                stroke="#64748B"
                tick={{ fill: '#94A3B8', fontSize: 12 }}
                axisLine={{ stroke: '#334155' }}
                allowDecimals={false}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '16px', fontSize: '12px' }}
              />
              <Bar
                dataKey="current_week_plays"
                name="Tuần này"
                fill="#1DB954"
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
              />
              <Bar
                dataKey="previous_week_plays"
                name="Tuần trước"
                fill="#6366F1"
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};
