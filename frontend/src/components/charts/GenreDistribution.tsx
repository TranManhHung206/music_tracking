import React from 'react';
import { Layers, Disc3 } from 'lucide-react';
import type { GenreDistributionData } from '../../types/analytics';

export interface GenreDistributionProps {
  data: GenreDistributionData;
  title?: string;
}

export const GenreDistribution: React.FC<GenreDistributionProps> = ({
  data,
  title = 'Phân Bố Thể Loại Âm Nhạc (Music Genres)',
}) => {
  const { genres, top_genre, total_plays } = data;

  if (!genres || genres.length === 0) {
    return (
      <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <h3 className="text-base sm:text-lg font-bold text-white mb-2">{title}</h3>
        <p className="text-xs text-slate-400">Chưa có dữ liệu phân loại thể loại trong kỳ này.</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/25 font-bold">
              Top: {top_genre}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
            Phân tích tỷ trọng các dòng nhạc chủ đạo qua {total_plays} lượt nghe
          </p>
        </div>

        <div className="flex items-center space-x-1.5 text-xs text-slate-400">
          <Layers className="w-4 h-4 text-slate-500" />
          <span>{genres.length} Thể loại</span>
        </div>
      </div>

      {/* Multi-segment Stacked Bar (Last.fm & Stream style) */}
      <div className="w-full h-4 rounded-full bg-slate-900 overflow-hidden flex shadow-inner border border-slate-800">
        {genres.map((g) => (
          <div
            key={g.name}
            style={{
              width: `${g.percentage}%`,
              backgroundColor: g.color || '#1DB954',
            }}
            className="h-full transition-all duration-500 hover:opacity-90 relative group"
            title={`${g.name}: ${g.percentage}% (${g.plays} lượt)`}
          />
        ))}
      </div>

      {/* Genre Tags Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-2">
        {genres.map((g) => (
          <div
            key={g.name}
            className="p-3 rounded-xl bg-[#0B0F17]/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between group"
          >
            <div className="flex items-center space-x-2 mb-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: g.color || '#1DB954' }}
              />
              <span className="text-xs font-bold text-slate-200 truncate group-hover:text-white">
                {g.name}
              </span>
            </div>

            <div className="flex items-end justify-between text-xs">
              <span className="text-[11px] text-slate-400">
                {g.plays} lượt
              </span>
              <span
                className="font-black text-sm"
                style={{ color: g.color || '#1DB954' }}
              >
                {g.percentage}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className="flex items-center space-x-2 text-[11px] text-slate-500 pt-1 border-t border-slate-800/60">
        <Disc3 className="w-3.5 h-3.5 text-slate-500" />
        <span>Phân loại tự động theo hồ sơ nghệ sĩ, danh mục nhạc cụ và nhịp điệu từ Spotify Pipeline.</span>
      </div>
    </div>
  );
};
