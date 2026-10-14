import React, { useState } from 'react';
import type {
  HeatmapCell,
  MonthHeatmapData,
  YearHeatmapData,
  MonthHeatmapDay,
  YearHeatmapDay,
} from '../../types/analytics';

export type { HeatmapCell };

export interface ListeningHeatmapProps {
  data: HeatmapCell[];
  periodType?: 'week' | 'month' | 'year';
  monthCalendar?: MonthHeatmapData;
  yearCalendar?: YearHeatmapData;
  selectedPeriodLabel?: string;
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

export const ListeningHeatmap: React.FC<ListeningHeatmapProps> = ({
  data,
  periodType = 'week',
  monthCalendar,
  yearCalendar,
  selectedPeriodLabel,
}) => {
  const [hoveredWeekCell, setHoveredWeekCell] = useState<{ day: number; hour: number; count: number } | null>(null);
  const [hoveredMonthDay, setHoveredMonthDay] = useState<MonthHeatmapDay | null>(null);
  const [hoveredYearDay, setHoveredYearDay] = useState<YearHeatmapDay | null>(null);

  // 1. Logic cho che do Tuan (7x24)
  const maxWeekCount = Math.max(...(data || []).map((d) => d.count), 1);

  const getWeekCellColor = (count: number) => {
    if (count === 0) return 'bg-[#1E293B]/40 hover:bg-[#1E293B]';
    const ratio = count / maxWeekCount;
    if (ratio < 0.25) return 'bg-emerald-950/80 text-emerald-400 hover:bg-emerald-900';
    if (ratio < 0.5) return 'bg-emerald-800 text-emerald-200 hover:bg-emerald-700';
    if (ratio < 0.75) return 'bg-emerald-600 text-white hover:bg-emerald-500';
    return 'bg-[#1DB954] text-black font-bold hover:bg-[#1ED760]';
  };

  const getWeekCount = (day: number, hour: number) => {
    const item = data?.find((d) => d.day_of_week === day && d.hour === hour);
    return item ? item.count : 0;
  };

  // 2. Logic cho che do Thang (Lich ban 7 cot x 5 hang)
  const monthMax = monthCalendar?.max_density || Math.max(...(monthCalendar?.days || []).map((d) => d.count), 1);

  const getMonthDayColor = (count: number) => {
    if (count === 0) return 'bg-[#1E293B]/40 border-slate-800/80 hover:border-slate-600 text-slate-500';
    const ratio = count / monthMax;
    if (ratio < 0.25) return 'bg-emerald-950/70 border-emerald-900/60 hover:border-emerald-700 text-emerald-300';
    if (ratio < 0.5) return 'bg-emerald-800/80 border-emerald-700/70 hover:border-emerald-500 text-emerald-100';
    if (ratio < 0.75) return 'bg-emerald-600/90 border-emerald-500/80 hover:border-emerald-400 text-white';
    return 'bg-[#1DB954] border-[#1ED760] text-slate-950 font-bold hover:brightness-110 shadow-sm shadow-[#1DB954]/20';
  };

  // 3. Logic cho che do Nam (53 tuan x 7 ngay)
  const yearMax = yearCalendar?.max_density || Math.max(...(yearCalendar?.days || []).map((d) => d.count), 1);

  const getYearDayColor = (count: number, isInRange: boolean) => {
    if (!isInRange) return 'opacity-0 pointer-events-none';
    if (count === 0) return 'bg-[#1E293B]/45 hover:bg-slate-700';
    const ratio = count / yearMax;
    if (ratio < 0.25) return 'bg-emerald-950 hover:bg-emerald-900';
    if (ratio < 0.5) return 'bg-emerald-800 hover:bg-emerald-700';
    if (ratio < 0.75) return 'bg-emerald-600 hover:bg-emerald-500';
    return 'bg-[#1DB954] hover:bg-[#1ED760]';
  };

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl transition-all">
      {/* Header & Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            {periodType === 'month'
              ? 'Mật Độ Nghe Nhạc Lịch Tháng (Monthly Heatmap)'
              : periodType === 'year'
              ? 'Bản Đồ Hoạt Động Cả Năm (Annual Activity Graph)'
              : 'Mật Độ Nghe Nhạc 24x7 (Listening Heatmap)'}
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            {selectedPeriodLabel
              ? `Chu kỳ: ${selectedPeriodLabel}`
              : periodType === 'month'
              ? 'Phân bổ lượt nghe theo từng ngày trong tháng'
              : periodType === 'year'
              ? 'Toàn bộ chuỗi ngày thưởng thức âm nhạc qua 53 tuần trong năm'
              : 'Khung giờ bạn hay đắm chìm vào âm nhạc nhất trong tuần'}
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-1.5 text-[11px] text-slate-400 shrink-0">
          <span>Ít</span>
          <span className="w-2.5 h-2.5 rounded-xs bg-[#1E293B]/40 inline-block border border-slate-800" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-950 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-800 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-emerald-600 inline-block" />
          <span className="w-2.5 h-2.5 rounded-xs bg-[#1DB954] inline-block" />
          <span>Nhiều</span>
        </div>
      </div>

      {/* RENDER CHE DO THANG */}
      {periodType === 'month' && monthCalendar && (
        <div className="space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-2 p-3 bg-[#0B0F17]/60 border border-[#1E293B]/80 rounded-xl text-center text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Tổng Lượt Nghe</span>
              <strong className="text-base font-bold text-white font-mono">{monthCalendar.total_plays}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Ngày Cao Điểm</span>
              <strong className="text-base font-bold text-[#1DB954] font-mono">
                {formatDateDMY(monthCalendar.peak_day)}
              </strong>
              <span className="text-[10px] text-slate-500 block">({monthCalendar.peak_plays} lượt)</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Ngày Hoạt Động</span>
              <strong className="text-base font-bold text-white font-mono">
                {monthCalendar.active_days} / {monthCalendar.total_days}
              </strong>
            </div>
          </div>

          {/* Calendar Table Grid */}
          <div className="overflow-x-auto pb-1">
            <div className="min-w-[420px]">
              {/* Day of Week Headers */}
              <div className="grid grid-cols-7 gap-1.5 mb-1.5 text-center text-xs font-semibold text-slate-400">
                {DAYS_SHORT.map((day) => (
                  <div key={day} className="py-1">
                    {day}
                  </div>
                ))}
              </div>

              {/* Days Cells */}
              <div className="grid grid-cols-7 gap-1.5">
                {/* Empty Offset Days before 1st of month */}
                {Array.from({ length: Math.max(0, monthCalendar.first_day_weekday - 1) }).map((_, idx) => (
                  <div
                    key={`empty-start-${idx}`}
                    className="h-14 rounded-lg bg-[#1E293B]/10 border border-dashed border-[#1E293B]/30 opacity-30"
                  />
                ))}

                {/* Actual Days */}
                {monthCalendar.days.map((day) => (
                  <div
                    key={day.date}
                    onMouseEnter={() => setHoveredMonthDay(day)}
                    onMouseLeave={() => setHoveredMonthDay(null)}
                    className={`h-14 rounded-lg border p-1.5 flex flex-col justify-between transition-all cursor-pointer relative group ${getMonthDayColor(
                      day.count
                    )}`}
                    title={`Ngày ${formatDateDMY(day.date)}: ${day.count} lượt nghe`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono font-semibold">{day.day_number}</span>
                      {day.count > 0 && (
                        <span className="text-[9px] px-1 py-0.2 rounded-full bg-black/30 font-mono">
                          {day.count}
                        </span>
                      )}
                    </div>
                    <div className="text-right text-[10px] opacity-75 font-mono">
                      {day.count > 0 ? `${day.count} tracks` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Hover Details Preview */}
          <div className="pt-2 border-t border-[#1E293B] text-xs text-slate-400 min-h-[24px]">
            {hoveredMonthDay ? (
              <span>
                Ngày <strong className="text-white">{formatDateDMY(hoveredMonthDay.date)}</strong> (
                {DAYS_SHORT[hoveredMonthDay.day_of_week - 1]}):{' '}
                <strong className="text-[#1DB954]">{hoveredMonthDay.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-slate-500 italic">Rê chuột vào từng ngày để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      )}

      {/* RENDER CHE DO NAM */}
      {periodType === 'year' && yearCalendar && (
        <div className="space-y-4">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 bg-[#0B0F17]/60 border border-[#1E293B]/80 rounded-xl text-center text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Tổng Lượt Nghe</span>
              <strong className="text-base font-bold text-white font-mono">{yearCalendar.total_plays}</strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Chuỗi Nghe Liên Tục</span>
              <strong className="text-base font-bold text-emerald-400 font-mono">
                {yearCalendar.longest_streak} ngày
              </strong>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Tháng Cao Điểm</span>
              <strong className="text-base font-bold text-[#1DB954] font-mono">
                Tháng {yearCalendar.top_month}
              </strong>
              <span className="text-[10px] text-slate-500 block">({yearCalendar.top_month_plays} lượt)</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Ngày Đỉnh Cao</span>
              <strong className="text-base font-bold text-white font-mono">
                {formatDateDMY(yearCalendar.peak_day)}
              </strong>
              <span className="text-[10px] text-slate-500 block">({yearCalendar.peak_plays} lượt)</span>
            </div>
          </div>

          {/* 53 Weeks x 7 Days Contribution Grid */}
          <div className="overflow-x-auto pb-2 scrollbar-thin">
            <div className="min-w-[760px]">
              {/* Month Header Row (Căn chỉnh đồng nhất 100% với 53 cột bên dưới) */}
              <div className="flex gap-1 mb-1.5 text-[10px] text-slate-400 font-mono">
                <div className="w-6 pr-1.5 shrink-0" />
                <div className="flex gap-1 flex-1">
                  {Array.from({ length: yearCalendar.total_weeks || 53 }).map((_, weekIdx) => {
                    const mh = yearCalendar.months_header.find((m) => m.start_week === weekIdx);
                    return (
                      <div
                        key={weekIdx}
                        className="w-2.5 sm:w-3 text-left font-semibold text-slate-400 relative shrink-0"
                      >
                        {mh && (
                          <span className="absolute left-0 top-0 whitespace-nowrap">
                            {mh.label}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Rows (T2 den CN) */}
              <div className="flex gap-1">
                {/* Day Labels Column */}
                <div className="flex flex-col gap-1 pr-1.5 text-[9px] text-slate-500 font-mono justify-between py-0.5 w-6 shrink-0 text-right">
                  <span>T2</span>
                  <span>T3</span>
                  <span>T4</span>
                  <span>T5</span>
                  <span>T6</span>
                  <span>T7</span>
                  <span>CN</span>
                </div>

                {/* 53 Columns of Weeks */}
                <div className="flex gap-1 flex-1">
                  {Array.from({ length: yearCalendar.total_weeks || 53 }).map((_, weekIdx) => {
                    const daysInWeek = yearCalendar.days.filter((d) => d.week_index === weekIdx);
                    return (
                      <div key={weekIdx} className="flex flex-col gap-1 shrink-0">
                        {Array.from({ length: 7 }).map((_, dayIdx) => {
                          const weekday = dayIdx + 1;
                          const day = daysInWeek.find((d) => d.day_of_week === weekday);
                          if (!day) {
                            return <div key={weekday} className="w-2.5 h-2.5 sm:w-3 sm:h-3 opacity-0" />;
                          }
                          return (
                            <div
                              key={day.date}
                              onMouseEnter={() => setHoveredYearDay(day)}
                              onMouseLeave={() => setHoveredYearDay(null)}
                              className={`w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-[2px] cursor-pointer transition-colors ${getYearDayColor(
                                day.count,
                                day.is_in_range
                              )}`}
                              title={`Ngày ${formatDateDMY(day.date)}: ${day.count} lượt nghe`}
                            />
                          );
                        })}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Hover Details Preview */}
          <div className="pt-2 border-t border-[#1E293B] text-xs text-slate-400 min-h-[24px]">
            {hoveredYearDay ? (
              <span>
                Ngày <strong className="text-white">{formatDateDMY(hoveredYearDay.date)}</strong> (
                {DAYS_SHORT[hoveredYearDay.day_of_week - 1]}):{' '}
                <strong className="text-[#1DB954]">{hoveredYearDay.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-slate-500 italic">Rê chuột vào từng ô vuông để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      )}

      {/* RENDER CHE DO TUAN (DEFAULT) */}
      {(periodType === 'week' || (!monthCalendar && !yearCalendar)) && (
        <div className="overflow-x-auto pb-2">
          <div className="min-w-[620px]">
            {/* Hours Header */}
            <div className="grid grid-cols-[36px_repeat(24,1fr)] gap-1 text-[10px] text-slate-500 mb-1.5 text-center font-mono">
              <div></div>
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
                    <span className="text-[11px] font-semibold text-slate-400 text-center">
                      {dayLabel}
                    </span>
                    {HOURS.map((hour) => {
                      const count = getWeekCount(dayNum, hour);
                      return (
                        <div
                          key={hour}
                          onMouseEnter={() => setHoveredWeekCell({ day: dayNum, hour, count })}
                          onMouseLeave={() => setHoveredWeekCell(null)}
                          className={`h-5 sm:h-6 rounded-xs transition-colors cursor-pointer flex items-center justify-center text-[9px] ${getWeekCellColor(
                            count
                          )}`}
                          title={`Thứ ${dayLabel}, ${hour}:00 - ${count} lượt nghe`}
                        />
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {/* Hover Details Preview */}
            <div className="mt-4 pt-3 border-t border-[#1E293B] text-xs text-slate-400 min-h-[24px]">
              {hoveredWeekCell ? (
                <span>
                  Thứ <strong className="text-white">{DAYS_SHORT[hoveredWeekCell.day - 1]}</strong> lúc{' '}
                  <strong className="text-[#1DB954]">{hoveredWeekCell.hour}:00</strong>: có{' '}
                  <strong className="text-white">{hoveredWeekCell.count} lượt nghe</strong>
                </span>
              ) : (
                <span className="text-slate-500 italic">Rê chuột vào từng ô để xem chi tiết lượt nghe</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
