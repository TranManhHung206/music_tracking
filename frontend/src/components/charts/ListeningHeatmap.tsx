import React, { useState } from 'react';
import type { HeatmapCell } from '../../types/analytics';

export type { HeatmapCell };

export interface ListeningHeatmapProps {
  data: HeatmapCell[];
}

const DAYS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export const ListeningHeatmap: React.FC<ListeningHeatmapProps> = ({ data }) => {
  const [hoveredCell, setHoveredCell] = useState<{ day: number; hour: number; count: number } | null>(null);

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  const getCellColor = (count: number) => {
    if (count === 0) return 'bg-[#1E293B]/40 hover:bg-[#1E293B]';
    const ratio = count / maxCount;
    if (ratio < 0.25) return 'bg-emerald-950/80 text-emerald-400 hover:bg-emerald-900';
    if (ratio < 0.5) return 'bg-emerald-800 text-emerald-200 hover:bg-emerald-700';
    if (ratio < 0.75) return 'bg-emerald-600 text-white hover:bg-emerald-500';
    return 'bg-[#1DB954] text-black font-bold hover:bg-[#1ED760]';
  };

  const getCount = (day: number, hour: number) => {
    const item = data.find((d) => d.day_of_week === day && d.hour === hour);
    return item ? item.count : 0;
  };

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            Mật Độ Nghe Nhạc 24x7 (Listening Heatmap)
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Khung giờ bạn hay đắm chìm vào âm nhạc nhất trong tuần
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-1 text-[11px] text-slate-400">
          <span>Ít</span>
          <span className="w-2.5 h-2.5 rounded-sm bg-[#1E293B]/40 inline-block" />
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-950 inline-block" />
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-800 inline-block" />
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-600 inline-block" />
          <span className="w-2.5 h-2.5 rounded-sm bg-[#1DB954] inline-block" />
          <span>Nhiều</span>
        </div>
      </div>

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
            {DAYS.map((dayLabel, index) => {
              const dayNum = index + 1;
              return (
                <div key={dayNum} className="grid grid-cols-[36px_repeat(24,1fr)] gap-1 items-center">
                  <span className="text-[11px] font-semibold text-slate-400 text-center">
                    {dayLabel}
                  </span>
                  {HOURS.map((hour) => {
                    const count = getCount(dayNum, hour);
                    return (
                      <div
                        key={hour}
                        onMouseEnter={() => setHoveredCell({ day: dayNum, hour, count })}
                        onMouseLeave={() => setHoveredCell(null)}
                        className={`h-5 sm:h-6 rounded-xs transition-colors cursor-pointer flex items-center justify-center text-[9px] ${getCellColor(
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
            {hoveredCell ? (
              <span>
                Thứ <strong className="text-white">{DAYS[hoveredCell.day - 1]}</strong> lúc{' '}
                <strong className="text-[#1DB954]">{hoveredCell.hour}:00</strong>: có{' '}
                <strong className="text-white">{hoveredCell.count} lượt nghe</strong>
              </span>
            ) : (
              <span className="text-slate-500 italic">Rê chuột vào từng ô để xem chi tiết lượt nghe</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
