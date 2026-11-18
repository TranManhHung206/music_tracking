import React from 'react';
import { Layers, Disc3 } from 'lucide-react';
import type { GenreDistributionData } from '../../types/analytics';
import { Card } from '../ui/Card';
import { ChartCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

export interface GenreDistributionProps {
  data: GenreDistributionData;
  title?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const GenreDistribution: React.FC<GenreDistributionProps> = ({
  data,
  title = 'Phân Bố Thể Loại Âm Nhạc (Music Genres)',
  isLoading = false,
  error = null,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <Card variant="default" padding="md">
        <ChartCardSkeleton heightClass="h-44" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="default" padding="md">
        <h3 className="text-base sm:text-lg font-bold text-white mb-3">{title}</h3>
        <SectionErrorState message={error} onRetry={onRetry} />
      </Card>
    );
  }

  const genres = Array.isArray(data?.genres) ? data.genres : [];
  const top_genre = data?.top_genre || 'Chưa có dữ liệu';
  const total_plays = data?.total_plays || 0;

  if (genres.length === 0) {
    return (
      <Card variant="default" padding="md">
        <h3 className="text-base sm:text-lg font-bold text-white mb-3">{title}</h3>
        <SectionEmptyState
          title="Chưa có dữ liệu thể loại âm nhạc"
          description="Chưa có đủ lượt nghe hoặc thông tin nghệ sĩ trong kỳ này để phân loại dòng nhạc."
          icon={<Disc3 className="w-5 h-5" />}
          compact
        />
      </Card>
    );
  }

  return (
    <Card variant="default" padding="md" className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-spotify-green/10 text-spotify-green border border-spotify-green/25 font-bold">
              Top: {top_genre}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-text-muted mt-0.5">
            Phân tích tỷ trọng các dòng nhạc chủ đạo qua {total_plays} lượt nghe
          </p>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-text-muted shrink-0">
          <Layers className="w-4 h-4 text-slate-400" />
          <span>{genres.length} Thể loại</span>
        </div>
      </div>

      {/* Multi-segment Stacked Bar */}
      <div
        role="img"
        aria-label={`Tỷ trọng thể loại: ${genres.map((g) => `${g.name} ${g.percentage}%`).join(', ')}`}
        className="w-full h-4 rounded-full bg-slate-900 overflow-hidden flex shadow-inner border border-slate-800"
      >
        {genres.map((g) => (
          <div
            key={g.name}
            style={{
              width: `${g.percentage}%`,
              backgroundColor: g.color || '#1DB954',
            }}
            className="h-full transition-all duration-500 hover:opacity-90"
            title={`${g.name}: ${g.percentage}% (${g.plays} lượt)`}
          />
        ))}
      </div>

      {/* Genre Tags Grid */}
      <div className="grid grid-cols-1 min-[360px]:grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-1">
        {genres.map((g) => (
          <div
            key={g.name}
            className="p-3 rounded-xl bg-obsidian-bg/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between group"
          >
            <div className="flex items-center gap-2 mb-2 min-w-0">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: g.color || '#1DB954' }}
                aria-hidden="true"
              />
              <span className="text-xs font-bold text-slate-200 truncate group-hover:text-white">
                {g.name}
              </span>
            </div>

            <div className="flex items-end justify-between text-xs">
              <span className="text-[11px] text-text-muted">{g.plays} lượt</span>
              <span
                className="font-black text-sm font-mono"
                style={{ color: g.color || '#1DB954' }}
              >
                {g.percentage}%
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className="flex items-center gap-2 text-[11px] text-text-muted pt-1 border-t border-slate-800/60">
        <Disc3 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>Phân loại theo hồ sơ nghệ sĩ, danh mục vùng nhạc và đặc trưng âm thanh của MusicTrack.</span>
      </div>
    </Card>
  );
};
