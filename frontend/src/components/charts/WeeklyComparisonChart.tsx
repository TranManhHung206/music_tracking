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
import { Card } from '../ui/Card';
import { ChartCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface WeeklyComparisonChartProps {
  data: WeeklyComparisonData;
  periodType?: CalendarPeriodType;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
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
      <div className="bg-obsidian-bg/95 border border-obsidian-border rounded-xl p-3 shadow-2xl backdrop-blur-md min-w-[190px]">
        <p className="text-xs font-bold text-white mb-2 flex items-center justify-between gap-3">
          <span>{point.label}</span>
          {point.full_label && point.full_label !== point.label && (
            <span className="text-[11px] text-text-muted font-normal">
              {point.full_label}
            </span>
          )}
        </p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2.5 h-2.5 rounded-sm bg-spotify-green" />
              <span>{currentSeriesName}:</span>
            </span>
            <span className="font-mono font-bold text-white">
              {point.current_plays} lượt
            </span>
          </div>
          <div className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-1.5 text-text-muted">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#6366F1]" />
              <span>{previousSeriesName}:</span>
            </span>
            <span className="font-mono text-slate-300">
              {point.previous_plays} lượt
            </span>
          </div>
          <div className="pt-1.5 border-t border-slate-800 flex items-center justify-between text-[11px]">
            <span className="text-text-muted">Chênh lệch:</span>
            <span
              className={`font-mono font-bold ${
                diff > 0
                  ? 'text-spotify-green'
                  : diff < 0
                  ? 'text-rose-400'
                  : 'text-text-muted'
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
  isLoading = false,
  error = null,
  onRetry,
}) => {
  const effectiveType: CalendarPeriodType = data?.period_type || periodType || 'week';

  const titleText =
    effectiveType === 'month'
      ? 'So Sánh Xu Hướng Nghe Nhạc Theo Tháng'
      : effectiveType === 'year'
      ? 'So Sánh Xu Hướng Nghe Nhạc Theo Năm'
      : 'So Sánh Lượt Nghe Theo Tuần';

  if (isLoading) {
    return (
      <Card variant="default" padding="md">
        <ChartCardSkeleton heightClass="h-64" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="default" padding="md">
        <h3 className="text-base sm:text-lg font-bold text-white mb-3">{titleText}</h3>
        <SectionErrorState message={error} onRetry={onRetry} />
      </Card>
    );
  }

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
    <Card variant="default" padding="md">
      {/* Header & Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-spotify-green shrink-0" />
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
              {titleText}
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-text-muted mt-0.5">
            {currentLabel} so với {previousLabel}
          </p>
        </div>

        {/* Quick Stat Badges */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="px-3 py-1.5 rounded-xl bg-obsidian-bg/70 border border-obsidian-border flex items-center gap-2">
            <span className="text-[11px] text-text-muted">{currentSeriesName}:</span>
            <span className="text-xs font-mono font-bold text-white">
              {totalCurrent} lượt
            </span>
          </div>

          {isNewActivity ? (
            <div className="px-3 py-1.5 rounded-xl border bg-emerald-950/40 border-emerald-500/30 text-spotify-green flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 shrink-0" />
              <span className="text-xs font-bold">Hoạt động mới</span>
            </div>
          ) : (
            <div
              className={`px-3 py-1.5 rounded-xl border flex items-center gap-1.5 ${
                isGrowth
                  ? 'bg-emerald-950/40 border-emerald-500/30 text-spotify-green'
                  : isDecline
                  ? 'bg-rose-950/40 border-rose-500/30 text-rose-400'
                  : 'bg-slate-900 border-slate-700 text-slate-300'
              }`}
            >
              {isGrowth ? (
                <TrendingUp className="w-3.5 h-3.5 shrink-0" />
              ) : isDecline ? (
                <TrendingDown className="w-3.5 h-3.5 shrink-0" />
              ) : (
                <Minus className="w-3.5 h-3.5 shrink-0" />
              )}
              <span className="text-xs font-mono font-bold">
                {growthVal > 0 ? `+${growthVal}%` : `${growthVal}%`}
              </span>
            </div>
          )}

          {peakPlays > 0 && peakLabel && (
            <div className="px-3 py-1.5 rounded-xl bg-obsidian-bg/70 border border-obsidian-border flex items-center gap-1.5 text-amber-400">
              <Zap className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span className="text-xs text-slate-200">
                Cao điểm: <strong className="text-white">{peakLabel}</strong> ({peakPlays} lượt)
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chart Canvas */}
      {seriesData.length === 0 || (totalCurrent === 0 && totalPrevious === 0) ? (
        <SectionEmptyState
          title="Chưa có dữ liệu so sánh"
          description="Chưa có lượt nghe nào được ghi nhận trong cả kỳ hiện tại lẫn kỳ đối chiếu trước đó."
          icon={<Calendar className="w-5 h-5" />}
        />
      ) : (
        <div className="w-full h-64 sm:h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={seriesData}
              margin={{ top: 10, right: 12, left: -12, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
              <XAxis
                dataKey="short_label"
                stroke="#94A3B8"
                tick={{ fill: '#94A3B8', fontSize: 11 }}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                stroke="#94A3B8"
                tick={{ fill: '#94A3B8', fontSize: 11 }}
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
                wrapperStyle={{ paddingBottom: '12px', fontSize: '12px' }}
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
    </Card>
  );
};
