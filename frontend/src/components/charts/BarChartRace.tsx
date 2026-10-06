import React, { useState, useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';
import type { TimelineFrame } from '../../types/analytics';

export type { TimelineFrame };

export interface BarChartRaceProps {
  timeline: TimelineFrame[];
  speedMs?: number;
}

export const BarChartRace: React.FC<BarChartRaceProps> = ({
  timeline,
  speedMs = 1500,
}) => {
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentFrameIndex((prev) => {
          if (prev >= timeline.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, speedMs);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, timeline.length, speedMs]);

  if (!timeline || timeline.length === 0) return null;

  const currentFrame = timeline[currentFrameIndex];
  const sortedRankings = [...currentFrame.rankings]
    .sort((a, b) => b.cumulative_plays - a.cumulative_plays)
    .slice(0, 5);

  const maxVal = Math.max(...sortedRankings.map((r) => r.cumulative_plays), 1);

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
  };

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-3">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            Bar Chart Race: Top Nghệ Sĩ Qua Các Tháng
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Xem sự dịch chuyển thứ hạng nghe nhạc lũy kế theo thời gian
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-3">
          <span className="text-lg sm:text-xl font-mono font-extrabold text-[#1DB954]">
            {currentFrame.date}
          </span>

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 rounded-xl bg-[#0B0F17] border border-[#1E293B] hover:border-[#1DB954] text-white hover:text-[#1DB954] transition-all cursor-pointer flex items-center justify-center"
            title={isPlaying ? 'Tạm dừng' : 'Chạy chuyển động'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>

          <button
            onClick={handleReset}
            className="p-2 rounded-xl bg-[#0B0F17] border border-[#1E293B] hover:border-slate-500 text-slate-400 hover:text-white transition-all cursor-pointer"
            title="Quay lại từ đầu"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Slider */}
      <div className="mb-6">
        <input
          type="range"
          min={0}
          max={timeline.length - 1}
          value={currentFrameIndex}
          onChange={(e) => {
            setIsPlaying(false);
            setCurrentFrameIndex(Number(e.target.value));
          }}
          className="w-full h-1.5 bg-[#0B0F17] rounded-lg appearance-none cursor-pointer accent-[#1DB954]"
        />
      </div>

      {/* Bars Stack */}
      <div className="space-y-3 min-h-[220px]">
        {sortedRankings.map((item, idx) => {
          const widthPct = Math.max((item.cumulative_plays / maxVal) * 100, 5);
          return (
            <div key={item.name} className="flex items-center text-xs">
              <span className="w-6 font-bold text-slate-500 text-center mr-2">
                #{idx + 1}
              </span>
              <div className="flex-1">
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-slate-200">{item.name}</span>
                  <span className="font-mono text-[#1DB954] font-bold">
                    {item.cumulative_plays} lượt
                  </span>
                </div>
                <div className="w-full bg-[#0B0F17] rounded-full h-3 overflow-hidden border border-[#1E293B]/50">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-600 to-[#1DB954] rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
