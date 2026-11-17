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
import { TrendingUp, TrendingDown, Minus, Zap, Calendar, Sparkles } from 'lucide-react';
import type {
  WeeklyComparisonData,
  ComparisonSeriesPoint,
  CalendarPeriodType,
} from '../../types/analytics';

interface WeeklyComparisonChartProps {
  data: WeeklyComparisonData;
  periodType?: CalendarPeriodType;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    dataKey: string;
    payload: ComparisonSeriesPoint;
  }>;
  currentSeriesName: string;
  previousSeriesName: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({
  active,
  payload,
  currentSeriesName,
  previousSeriesName,
}) => {
  if (active && payload && payload.length) {
    const point = payload[0].payload;
    const diff = point.diff;

    return (
      <div className="bg-[#0B0F17]/95 border border-[#1E293B] rounded-xl p-3 shadow-2xl backdrop-blur-md min-w-[190px]">
        <p className="text-xs font-bold text-white mb-2 flex items-center justify-between gap-3">
          <span>{point.label}</span>
          {point.full_label && point.full_label !== point.label && (
            <span className="text-[11px] text-slate-400 font-normal">
              {point.full_label}
            </span>
          )}
        </p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center space-x-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#1DB954]" />
              <span>{currentSeriesName}:</span>
            </span>
            <span className="font-mono font-bold text-white">
              {point.current_plays} lượt
            </span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center space-x-1.5 text-slate-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#6366F1]" />
              <span>{previousSeriesName}:</span>
            </span>
            <span className="font-mono text-slate-300">
              {point.previous_plays} lượt
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

export const WeeklyComparisonChart: React.FC<WeeklyComparisonChartProps> = ({
  data,
  periodType,
}) => {
  const effectiveType: CalendarPeriodType = data?.period_type || periodType || 'week';

  const summary = data?.summary || {
    total_current: 0,
    total_previous: 0,
    total_current_week: 0,
    total_previous_week: 0,
    growth_percentage: 0,
    baseline_status: 'empty' as const,
    peak_label: 'Thứ 2',
    peak_plays: 0,
    peak_day_current: 'Thứ 2',
    peak_plays_current: 0,
  };

  const totalCurrent = summary.total_current ?? summary.total_current_week ?? 0;
  const totalPrevious = summary.total_previous ?? summary.total_previous_week ?? 0;
  const peakLabel = summary.peak_label || summary.peak_day_current || '';
  const peakPlays = summary.peak_plays ?? summary.peak_plays_current ?? 0;
  const isNewActivity =
    summary.baseline_status === 'new_activity' ||
    (summary.growth_percentage === null && totalCurrent > 0 && totalPrevious === 0);

  const seriesData: ComparisonSeriesPoint[] =
    Array.isArray(data?.series) && data.series.length > 0
      ? data.series
      : (data?.days || []).map((d) => ({
          index: d.day_index,
          label: d.day_name,
          short_label: d.day_name,
          full_label: d.day_name_en,
          current_plays: d.current_week_plays,
          previous_plays: d.previous_week_plays,
          diff: d.diff,
        }));

  const currentLabel = data?.current_label || data?.current_week_label || 'Kỳ đang chọn';
  const previousLabel = data?.previous_label || data?.previous_week_label || 'Kỳ trước';

  const titleText =
    effectiveType === 'month'
      ? 'So Sánh Xu Hướng Nghe Nhạc Theo Tháng'
      : effectiveType === 'year'
      ? 'So Sánh Xu Hướng Nghe Nhạc Theo Năm'
      : 'So Sánh Lượt Nghe Theo Tuần';

  const currentSeriesName =
    effectiveType === 'month'
      ? 'Tháng này'
      : effectiveType === 'year'
      ? 'Năm này'
      : 'Tuần này';
  const previousSeriesName =
    effectiveType === 'month'
      ? 'Tháng trước'
      : effectiveType === 'year'
      ? 'Năm trước'
      : 'Tuần trước';

  const growthVal = summary.growth_percentage ?? 0;
  const isGrowth = !isNewActivity && summary.growth_percentage !== null && growthVal > 0;
  const isDecline = !isNewActivity && summary.growth_percentage !== null && growthVal < 0;

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      {/* Header & Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center space-x-2">
            <Calendar className="w-5 h-5 text-[#1DB954]" />
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
              {titleText}
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            {currentLabel} so với {previousLabel}
          </p>
        </div>

        {/* Quick Stat Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="px-3 py-1.5 rounded-xl bg-[#0B0F17]/70 border border-[#1E293B] flex items-center space-x-2">
            <span className="text-[11px] text-slate-400">{currentSeriesName}:</span>
            <span className="text-xs font-mono font-bold text-white">
              {totalCurrent}
            </span>
          </div>

          {isNewActivity ? (
            <div className="px-3 py-1.5 rounded-xl border bg-emerald-950/40 border-emerald-500/30 text-[#1DB954] flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span className="text-xs font-bold">Hoạt động mới</span>
            </div>
          ) : (
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
                {growthVal > 0 ? `+${growthVal}%` : `${growthVal}%`}
              </span>
            </div>
          )}

          {peakPlays > 0 && peakLabel && (
            <div className="px-3 py-1.5 rounded-xl bg-[#0B0F17]/70 border border-[#1E293B] flex items-center space-x-1.5 text-amber-400">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-xs text-slate-300">
                Cao điểm: <strong className="text-white">{peakLabel}</strong> ({peakPlays} lượt)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chart Canvas */}
      {seriesData.length === 0 || (totalCurrent === 0 && totalPrevious === 0) ? (
        <div className="h-64 flex flex-col items-center justify-center text-slate-500 text-xs bg-[#0B0F17]/30 rounded-xl border border-[#1E293B]/40">
          <p>Chưa có dữ liệu lượt nghe để so sánh trong hai kỳ này.</p>
        </div>
      ) : (
        <div className="w-full h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={seriesData}
              margin={{ top: 10, right: 15, left: -20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis
                dataKey="short_label"
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
              <Tooltip
                content={
                  <CustomTooltip
                    currentSeriesName={currentSeriesName}
                    previousSeriesName={previousSeriesName}
                  />
                }
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '16px', fontSize: '12px' }}
              />
              <Bar
                dataKey="current_plays"
                name={currentSeriesName}
                fill="#1DB954"
                radius={[6, 6, 0, 0]}
                maxBarSize={32}
              />
              <Bar
                dataKey="previous_plays"
                name={previousSeriesName}
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
