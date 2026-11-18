import React, { useState, useMemo } from 'react';
import { CalendarOff } from 'lucide-react';
import type {
  HeatmapCell,
  MonthHeatmapData,
  YearHeatmapData,
  MonthHeatmapDay,
  YearHeatmapDay,
} from '../../types/analytics';
import { Card } from '../ui/Card';
import { ChartCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

export type { HeatmapCell };

export interface ListeningHeatmapProps {
  data: HeatmapCell[];
  periodType?: 'week' | 'month' | 'year';
  monthCalendar?: MonthHeatmapData;
  yearCalendar?: YearHeatmapData;
  selectedPeriodLabel?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const DAYS_SHORT = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

const formatDateDMY = (dateStr?: string): string => {
  if (!dateStr) return '--';
  const clean = dateStr.split('T')[0];
  const parts = clean.split('-');
  if (parts.length === 3 && parts[0].length === 4) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
};

type HeatmapSelection =
  | { scopeKey: string; kind: 'week'; week: { day: number; hour: number; count: number } }
  | { scopeKey: string; kind: 'month'; month: MonthHeatmapDay }
  | { scopeKey: string; kind: 'year'; year: YearHeatmapDay };

export const ListeningHeatmap: React.FC<ListeningHeatmapProps> = ({
  data,
  periodType = 'week',
  monthCalendar,
  yearCalendar,
  selectedPeriodLabel,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  const scopeKey = `${periodType}:${selectedPeriodLabel || ''}:${monthCalendar?.year || ''}-${monthCalendar?.month || ''}:${yearCalendar?.year || ''}`;

  const [hoveredWeekCell, setHoveredWeekCell] = useState<{ day: number; hour: number; count: number } | null>(null);
  const [hoveredMonthDay, setHoveredMonthDay] = useState<MonthHeatmapDay | null>(null);
  const [hoveredYearDay, setHoveredYearDay] = useState<YearHeatmapDay | null>(null);
  const [selection, setSelection] = useState<HeatmapSelection | null>(null);

  const activeSelection = selection && selection.scopeKey === scopeKey ? selection : null;

  const safeData = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const { weekCountMap, maxWeekCount, weekTotalPlays } = useMemo(() => {
    const map = new Map<string, number>();
    let maxCount = 1;
    let total = 0;
    for (const item of safeData) {
      if (!item) continue;
      const count = item.count || 0;
      total += count;
      if (count > maxCount) maxCount = count;
      map.set(`${item.day_of_week}-${item.hour}`, count);
    }
    return { weekCountMap: map, maxWeekCount: maxCount, weekTotalPlays: total };
  }, [safeData]);

  const monthMax = useMemo(() => {
    if (monthCalendar?.max_density) return monthCalendar.max_density;
    const days = Array.isArray(monthCalendar?.days) ? monthCalendar.days : [];
    let maxDensity = 1;
    for (const d of days) {
      if (d.count > maxDensity) maxDensity = d.count;
    }
    return maxDensity;
  }, [monthCalendar]);

  const { yearGridMap, monthHeaderMap, yearMax } = useMemo(() => {
    const grid = new Map<string, YearHeatmapDay>();
    const headers = new Map<number, string>();
    const days = Array.isArray(yearCalendar?.days) ? yearCalendar.days : [];
    const headerList = Array.isArray(yearCalendar?.months_header) ? yearCalendar.months_header : [];

    let maxDensity = yearCalendar?.max_density || 1;
    for (const d of days) {
      grid.set(`${d.week_index}-${d.day_of_week}`, d);
      if (!yearCalendar?.max_density && d.count > maxDensity) {
        maxDensity = d.count;
      }
    }
    for (const h of headerList) {
      headers.set(h.start_week, h.label);
    }
    return { yearGridMap: grid, monthHeaderMap: headers, yearMax: maxDensity };
  }, [yearCalendar]);

  const titleText =
    periodType === 'month'
      ? 'Mật Độ Nghe Nhạc Lịch Tháng'
      : periodType === 'year'
      ? 'Bản Đồ Hoạt Động Cả Năm'
      : 'Mật Độ Nghe Nhạc 24x7';

  const subtitleText = selectedPeriodLabel
    ? `Chu kỳ: ${selectedPeriodLabel}`
    : periodType === 'month'
    ? 'Phân bổ lượt nghe theo từng ngày trong tháng'
    : periodType === 'year'
    ? 'Chuỗi ngày nghe nhạc qua 53 tuần trong năm'
    : 'Khung giờ bạn nghe nhạc nhiều nhất trong tuần';

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
        <div className="mb-4">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{titleText}</h3>
          <p className="text-xs sm:text-sm text-text-muted">{subtitleText}</p>
        </div>
        <SectionErrorState message={error} onRetry={onRetry} />
      </Card>
    );
  }

  const isMonthEmpty = periodType === 'month' && monthCalendar && monthCalendar.total_plays === 0;
  const isYearEmpty = periodType === 'year' && yearCalendar && yearCalendar.total_plays === 0;
  const isWeekEmpty =
    (periodType === 'week' ||
      (periodType === 'month' && !monthCalendar) ||
      (periodType === 'year' && !yearCalendar)) &&
    weekTotalPlays === 0;

  if (isMonthEmpty || isYearEmpty || isWeekEmpty) {
    return (
      <Card variant="default" padding="md" className="flex flex-col justify-between">
        <div className="mb-4">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{titleText}</h3>
          <p className="text-xs sm:text-sm text-text-muted">{subtitleText}</p>
        </div>
        <SectionEmptyState
          title="Chưa có hoạt động nghe nhạc"
          description="Không có lượt nghe nào được ghi nhận trong kỳ này để dựng bản đồ mật độ."
          icon={<CalendarOff className="w-5 h-5" />}
        />
      </Card>
    );
  }

  const getWeekCellColor = (count: number) => {
    if (count === 0) return 'bg-obsidian-border/45 text-slate-400 hover:bg-obsidian-border';
    const ratio = count / maxWeekCount;
    if (ratio < 0.25) return 'bg-emerald-950/85 text-emerald-300 hover:bg-emerald-900';
    if (ratio < 0.5) return 'bg-emerald-800 text-emerald-100 hover:bg-emerald-700';
    if (ratio < 0.75) return 'bg-emerald-600 text-white hover:bg-emerald-500';
    return 'bg-spotify-green text-black font-bold hover:bg-spotify-hover';
  };

  const getWeekCount = (day: number, hour: number) => weekCountMap.get(`${day}-${hour}`) ?? 0;

  const getMonthDayColor = (count: number) => {
    if (count === 0) return 'bg-obsidian-border/40 border-slate-800/80 hover:border-slate-600 text-slate-400';
    const ratio = count / monthMax;
    if (ratio < 0.25) return 'bg-emerald-950/75 border-emerald-900/60 hover:border-emerald-700 text-emerald-200';
    if (ratio < 0.5) return 'bg-emerald-800/80 border-emerald-700/70 hover:border-emerald-500 text-emerald-100';
    if (ratio < 0.75) return 'bg-emerald-600/90 border-emerald-500/80 hover:border-emerald-400 text-white';
    return 'bg-spotify-green border-spotify-hover text-slate-950 font-bold hover:brightness-110 shadow-sm shadow-spotify-green/20';
  };

  const getYearDayColor = (count: number, isInRange: boolean) => {
    if (!isInRange) return 'opacity-0 pointer-events-none';
    if (count === 0) return 'bg-obsidian-border/50 hover:bg-slate-700';
    const ratio = count / yearMax;
    if (ratio < 0.25) return 'bg-emerald-950 hover:bg-emerald-900';
    if (ratio < 0.5) return 'bg-emerald-800 hover:bg-emerald-700';
    if (ratio < 0.75) return 'bg-emerald-600 hover:bg-emerald-500';
    return 'bg-spotify-green hover:bg-spotify-hover';
  };

  const activeWeekCell =
    hoveredWeekCell || (activeSelection?.kind === 'week' ? activeSelection.week : null);
  const activeMonthDay =
    hoveredMonthDay || (activeSelection?.kind === 'month' ? activeSelection.month : null);
  const activeYearDay =
    hoveredYearDay || (activeSelection?.kind === 'year' ? activeSelection.year : null);

  return (
    <Card variant="default" padding="md">
      {/* Header & Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div className="min-w-0">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            {titleText}
          </h3>
          <p className="text-xs sm:text-sm text-text-muted">{subtitleText}</p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-1.5 text-[11px] text-text-muted shrink-0" aria-hidden="true">
          <span>Ít</span>
          <span className="w-2.5 h-2.5 rounded-xs bg-obsidian-border/45 inline-block border border-slate-700" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-950 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-800 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-600 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-spotify-green inline-block" />
          <span>Nhiều</span>
        </div>
      </div>

      {/* CHẾ ĐỘ THÁNG */}
      {periodType === 'month' && monthCalendar && (
        <div className="space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-1 min-[360px]:grid-cols-3 gap-2 p-3 bg-obsidian-bg/60 border border-obsidian-border/80 rounded-xl text-center text-xs">
            <div>
              <span className="text-text-muted block text-[11px]">Tổng Lượt Nghe</span>
              <strong className="text-base font-bold text-white font-mono">{monthCalendar.total_plays}</strong>
            </div>
            <div>
              <span className="text-text-muted block text-[11px]">Ngày Cao Điểm</span>
              <strong className="text-sm sm:text-base font-bold text-spotify-green font-mono">
                {formatDateDMY(monthCalendar.peak_day)}
              </strong>
              <span className="text-[11px] text-text-muted block">({monthCalendar.peak_plays} lượt)</span>
            </div>
            <div>
              <span className="text-text-muted block text-[11px]">Ngày Hoạt Động</span>
              <strong className="text-base font-bold text-white font-mono">
                {monthCalendar.active_days} / {monthCalendar.total_days}
              </strong>
            </div>
          </div>

          {/* Calendar Table Grid - Không cần cuộn ngang trên mobile */}
          <div>
            <div className="grid grid-cols-7 gap-1 sm:gap-1.5 mb-1.5 text-center text-[11px] sm:text-xs font-semibold text-text-muted">
              {DAYS_SHORT.map((day) => (
                <div key={day} className="py-1">
                  {day}
                </div>
              ))}
            </div>

            <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
              {Array.from({ length: Math.max(0, monthCalendar.first_day_weekday - 1) }).map((_, idx) => (
                <div
                  key={`empty-start-${idx}`}
                  aria-hidden="true"
                  className="h-11 sm:h-14 rounded-lg bg-obsidian-border/15 border border-dashed border-obsidian-border/35 opacity-40"
                />
              ))}

              {monthCalendar.days.map((day) => {
                const isSelected = activeSelection?.kind === 'month' && activeSelection.month.date === day.date;
                return (
                  <button
                    key={day.date}
                    type="button"
                    onClick={() => setSelection({ scopeKey, kind: 'month', month: day })}
                    onMouseEnter={() => setHoveredMonthDay(day)}
                    onMouseLeave={() => setHoveredMonthDay(null)}
                    aria-pressed={isSelected}
                    aria-label={`Ngày ${formatDateDMY(day.date)}, ${day.count} lượt nghe`}
                    className={`h-11 sm:h-14 rounded-lg border p-1 sm:p-1.5 flex flex-col justify-between transition-all cursor-pointer text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white ${getMonthDayColor(
                      day.count
                    )} ${isSelected ? 'ring-2 ring-white ring-offset-1 ring-offset-obsidian-bg' : ''}`}
                    title={`Ngày ${formatDateDMY(day.date)}: ${day.count} lượt nghe`}
                  >
                    <div className="flex items-center justify-between gap-0.5 w-full">
                      <span className="text-[11px] font-mono font-semibold leading-none">{day.day_number}</span>
                      {day.count > 0 && (
                        <span className="text-[11px] px-1 rounded-full bg-black/35 font-mono leading-tight">
                          {day.count}
                        </span>
                      )}
                    </div>
                    <div className="hidden sm:block text-right text-[11px] opacity-85 font-mono leading-none">
                      {day.count > 0 ? `${day.count} lượt` : ''}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selection / Hover Details Preview */}
          <div className="pt-2.5 border-t border-obsidian-border text-xs text-slate-300 min-h-[26px]">
            {activeMonthDay ? (
              <span>
                Ngày <strong className="text-white">{formatDateDMY(activeMonthDay.date)}</strong> (
                {DAYS_SHORT[activeMonthDay.day_of_week - 1]}):{' '}
                <strong className="text-spotify-green">{activeMonthDay.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-text-muted">Chạm hoặc rê chuột vào từng ngày để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      )}

      {/* CHẾ ĐỘ NĂM */}
      {periodType === 'year' && yearCalendar && (
        <div className="space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-obsidian-bg/60 border border-obsidian-border/80 rounded-xl text-center text-xs">
            <div>
              <span className="text-text-muted block text-[11px]">Tổng Lượt Nghe</span>
              <strong className="text-base font-bold text-white font-mono">{yearCalendar.total_plays}</strong>
            </div>
            <div>
              <span className="text-text-muted block text-[11px]">Chuỗi Nghe Liên Tục</span>
              <strong className="text-base font-bold text-emerald-400 font-mono">
                {yearCalendar.longest_streak} ngày
              </strong>
            </div>
            <div>
              <span className="text-text-muted block text-[11px]">Tháng Cao Điểm</span>
              <strong className="text-base font-bold text-spotify-green font-mono">
                Tháng {yearCalendar.top_month}
              </strong>
              <span className="text-[11px] text-text-muted block">({yearCalendar.top_month_plays} lượt)</span>
            </div>
            <div>
              <span className="text-text-muted block text-[11px]">Ngày Đỉnh Cao</span>
              <strong className="text-base font-bold text-white font-mono">
                {formatDateDMY(yearCalendar.peak_day)}
              </strong>
              <span className="text-[11px] text-text-muted block">({yearCalendar.peak_plays} lượt)</span>
            </div>
          </div>

          <p className="text-[11px] text-text-muted lg:hidden">
            Vuốt ngang bảng bên dưới để xem đủ 53 tuần trong năm
          </p>

          {/* 53 Weeks x 7 Days Contribution Grid */}
          <div className="w-full min-w-0 overflow-x-auto pb-2 scrollbar-thin">
            <div className="min-w-[740px]">
              <div className="flex gap-1 mb-2 text-[11px] text-text-muted font-mono h-4">
                <div className="w-7 pr-1.5 shrink-0" />
                <div className="flex gap-1 flex-1">
                  {Array.from({ length: yearCalendar.total_weeks || 53 }).map((_, weekIdx) => {
                    const monthLabel = monthHeaderMap.get(weekIdx);
                    return (
                      <div
                        key={weekIdx}
                        className="w-3 text-left font-semibold text-text-muted relative shrink-0"
                      >
                        {monthLabel && (
                          <span className="absolute left-0 top-0 whitespace-nowrap">
                            {monthLabel}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex gap-1">
                <div className="flex flex-col gap-1 pr-1.5 text-[11px] text-text-muted font-mono justify-between py-0.5 w-7 shrink-0 text-right leading-none">
                  <span>T2</span>
                  <span>T3</span>
                  <span>T4</span>
                  <span>T5</span>
                  <span>T6</span>
                  <span>T7</span>
                  <span>CN</span>
                </div>

                <div className="flex gap-1 flex-1">
                  {Array.from({ length: yearCalendar.total_weeks || 53 }).map((_, weekIdx) => (
                      <div key={weekIdx} className="flex flex-col gap-1 shrink-0">
                        {Array.from({ length: 7 }).map((_, dayIdx) => {
                          const weekday = dayIdx + 1;
                          const day = yearGridMap.get(`${weekIdx}-${weekday}`);
                          if (!day) {
                            return <div key={weekday} className="w-3 h-3 opacity-0" aria-hidden="true" />;
                          }
                          const isSelected = activeSelection?.kind === 'year' && activeSelection.year.date === day.date;
                          if (!day.is_in_range) {
                            return <div key={day.date} className="w-3 h-3 opacity-0" aria-hidden="true" />;
                          }
                          return (
                            <button
                              key={day.date}
                              type="button"
                              onClick={() => setSelection({ scopeKey, kind: 'year', year: day })}
                              onMouseEnter={() => setHoveredYearDay(day)}
                              onMouseLeave={() => setHoveredYearDay(null)}
                              aria-pressed={isSelected}
                              aria-label={`Ngày ${formatDateDMY(day.date)}, ${day.count} lượt nghe`}
                              className={`block w-3 h-3 rounded-[2px] cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white ${getYearDayColor(
                                day.count,
                                day.is_in_range
                              )} ${isSelected ? 'ring-2 ring-white' : ''}`}
                              title={`Ngày ${formatDateDMY(day.date)}: ${day.count} lượt nghe`}
                            />
                          );
                        })}
                      </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2.5 border-t border-obsidian-border text-xs text-slate-300 min-h-[26px]">
            {activeYearDay ? (
              <span>
                Ngày <strong className="text-white">{formatDateDMY(activeYearDay.date)}</strong> (
                {DAYS_SHORT[activeYearDay.day_of_week - 1]}):{' '}
                <strong className="text-spotify-green">{activeYearDay.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-text-muted">Chạm hoặc rê chuột vào từng ô để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      )}

      {/* CHẾ ĐỘ TUẦN (HOẶC FALLBACK KHI CHƯA CÓ LỊCH THÁNG/NĂM) */}
      {(periodType === 'week' ||
        (periodType === 'month' && !monthCalendar) ||
        (periodType === 'year' && !yearCalendar)) && (
        <div>
          <p className="text-[11px] text-text-muted md:hidden mb-2">
            Vuốt ngang bảng bên dưới để xem đủ 24 khung giờ
          </p>

          <div className="w-full min-w-0 overflow-x-auto pb-2 scrollbar-thin">
            <div className="min-w-[600px]">
              {/* Hours Header */}
              <div className="grid grid-cols-[36px_repeat(24,1fr)] gap-1 text-[11px] text-text-muted mb-1.5 text-center font-mono">
                <div />
                {HOURS.map((h) => (
                  <div key={h}>{h % 3 === 0 ? `${h}h` : ''}</div>
                ))}
              </div>

              {/* Grid Rows */}
              <div className="space-y-1">
                {DAYS_SHORT.map((dayLabel, index) => {
                  const dayNum = index + 1;
                  return (
                    <div key={dayNum} className="grid grid-cols-[36px_repeat(24,1fr)] gap-1 items-center">
                      <span className="text-[11px] font-semibold text-text-muted text-center">
                        {dayLabel}
                      </span>
                      {HOURS.map((hour) => {
                        const count = getWeekCount(dayNum, hour);
                        const isSelected =
                          activeSelection?.kind === 'week' &&
                          activeSelection.week.day === dayNum &&
                          activeSelection.week.hour === hour;
                        return (
                          <button
                            key={hour}
                            type="button"
                            onClick={() =>
                              setSelection({
                                scopeKey,
                                kind: 'week',
                                week: { day: dayNum, hour, count },
                              })
                            }
                            onMouseEnter={() => setHoveredWeekCell({ day: dayNum, hour, count })}
                            onMouseLeave={() => setHoveredWeekCell(null)}
                            aria-pressed={isSelected}
                            aria-label={`${dayLabel}, ${hour} giờ, ${count} lượt nghe`}
                            className={`h-6 rounded-xs transition-colors cursor-pointer flex items-center justify-center text-[11px] font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white ${getWeekCellColor(
                              count
                            )} ${isSelected ? 'ring-2 ring-white' : ''}`}
                            title={`${dayLabel}, ${hour}:00 - ${count} lượt nghe`}
                          >
                            {count > 0 ? <span className="hidden lg:inline">{count}</span> : null}
                          </button>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-obsidian-border text-xs text-slate-300 min-h-[26px]">
            {activeWeekCell ? (
              <span>
                <strong className="text-white">{DAYS_SHORT[activeWeekCell.day - 1]}</strong> lúc{' '}
                <strong className="text-spotify-green">{activeWeekCell.hour}:00</strong>:{' '}
                <strong className="text-white">{activeWeekCell.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-text-muted">Chạm hoặc rê chuột vào từng ô giờ để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      )}
    </Card>
  );
};
