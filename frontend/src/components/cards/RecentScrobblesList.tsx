import React, { useState } from 'react';
import { History, Clock, Sparkles, Disc, ExternalLink, RotateCw, ChevronDown, ChevronUp } from 'lucide-react';
import type { ListeningHistoryRecord } from '../../types/analytics';
import { Card } from '../ui/Card';
import { ListCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface RecentScrobblesListProps {
  records: ListeningHistoryRecord[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onRetry?: () => void;
  onFindSimilar: (trackId: string, trackName: string) => void;
}

const formatRelativeTime = (isoString?: string): string => {
  if (!isoString) return 'Gần đây';
  try {
    const past = new Date(isoString).getTime();
    const now = Date.now();
    const diffSeconds = Math.floor((now - past) / 1000);

    if (isNaN(diffSeconds) || diffSeconds < 0) {
      return 'Vừa xong';
    }
    if (diffSeconds < 60) {
      return 'Vừa xong';
    }
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
      return `${diffMinutes} phút trước`;
    }
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) {
      return `${diffHours} giờ trước`;
    }
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) {
      return `${diffDays} ngày trước`;
    }

    const date = new Date(isoString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const mins = String(date.getMinutes()).padStart(2, '0');
    return `${day}/${month} lúc ${hours}:${mins}`;
  } catch {
    return 'Gần đây';
  }
};

const formatDuration = (ms?: number): string => {
  if (!ms || ms <= 0) return '--:--';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export const RecentScrobblesList: React.FC<RecentScrobblesListProps> = ({
  records = [],
  isLoading = false,
  error = null,
  onRefresh,
  onRetry,
  onFindSimilar,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const safeRecords = Array.isArray(records) ? records.filter((r) => r && r.track) : [];
  const displayLimit = isExpanded ? safeRecords.length : 6;
  const visibleRecords = safeRecords.slice(0, displayLimit);

  return (
    <Card variant="default" padding="md">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-obsidian-border">
        <div className="flex items-start sm:items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-spotify-green/10 border border-spotify-green/25 flex items-center justify-center text-spotify-green shrink-0">
            <History className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Nhật Ký Nghe Nhạc Gần Đây
              </h3>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-spotify-green/10 text-spotify-green border border-spotify-green/25">
                20 lượt phát mới nhất
              </span>
            </div>
            <p className="text-xs text-text-muted mt-0.5">
              Hiển thị các bài hát vừa phát gần nhất (không thay đổi theo bộ lọc Tuần / Tháng / Năm)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={isLoading}
              aria-label="Làm mới lịch sử nghe nhạc"
              className="min-h-[36px] flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-obsidian-bg border border-obsidian-border text-xs text-slate-200 hover:text-white hover:border-spotify-green/50 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              title="Làm mới lịch sử nghe nhạc"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-spotify-green' : ''}`} />
              <span>Làm mới</span>
            </button>
          )}
        </div>
      </div>

      {/* Nội dung */}
      {isLoading && safeRecords.length === 0 ? (
        <ListCardSkeleton rows={5} />
      ) : error && safeRecords.length === 0 ? (
        <SectionErrorState message={error} onRetry={onRetry || onRefresh} />
      ) : safeRecords.length === 0 ? (
        <SectionEmptyState
          title="Chưa có lượt nghe nào được ghi nhận"
          description="Hãy mở Spotify thưởng thức âm nhạc và nhấn Đồng bộ để cập nhật nhật ký mới nhất."
          icon={<History className="w-5 h-5" />}
        />
      ) : (
        <div className="space-y-2.5">
          {visibleRecords.map((item, idx) => {
            const track = item?.track;
            if (!track) return null;

            const albumImage = track.album?.image_url;
            const artistsText = Array.isArray(track.artists)
              ? track.artists.map((a) => a?.name).filter(Boolean).join(', ')
              : 'Nghệ sĩ chưa rõ';
            const spotifyUrl =
              track.spotify_id && !track.spotify_id.startsWith('mock')
                ? `https://open.spotify.com/track/${track.spotify_id}`
                : null;
            const durationMs = typeof track.duration_ms === 'number' ? track.duration_ms : 0;

            return (
              <div
                key={item.id || idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/70 hover:border-spotify-green/40 hover:bg-obsidian-bg/80 transition-all group gap-3"
              >
                {/* Bên trái: Ảnh album + Thông tin bài hát */}
                <div className="flex items-center gap-3 min-w-0">
                  {albumImage ? (
                    <img
                      src={albumImage}
                      alt={track.name}
                      className="w-11 h-11 rounded-lg object-cover border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <Disc className="w-5 h-5" />
                    </div>
                  )}

                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-spotify-green transition-colors">
                      {track.name}
                    </h4>
                    <p className="text-xs text-text-muted truncate">
                      {artistsText}
                      {track.album?.name ? ` • ${track.album.name}` : ''}
                    </p>
                  </div>
                </div>

                {/* Bên phải: Thời gian nghe + Thời lượng + Hành động */}
                <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pl-14 sm:pl-0">
                  <div className="text-left sm:text-right">
                    <div className="flex items-center sm:justify-end gap-1 text-xs font-medium text-slate-300">
                      <Clock className="w-3 h-3 text-spotify-green shrink-0" />
                      <span>{formatRelativeTime(item.played_at)}</span>
                    </div>
                    {durationMs > 0 && (
                      <span className="text-[11px] text-text-muted font-mono block">
                        {formatDuration(durationMs)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    {spotifyUrl && (
                      <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`Mở ${track.name} trên Spotify`}
                        className="min-w-[36px] min-h-[36px] p-2 rounded-lg bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-spotify-green hover:border-spotify-green/50 transition-all flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                        title="Mở trên Spotify"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}

                    <button
                      type="button"
                      onClick={() => onFindSimilar(track.spotify_id || '', track.name || '')}
                      aria-label={`Tìm bài hát tương đồng với ${track.name}`}
                      className="min-w-[36px] min-h-[36px] p-2 rounded-lg bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-spotify-green hover:border-spotify-green/50 transition-all cursor-pointer flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                      title="Gợi ý bài hát tương đồng bằng AI"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Nút Xem thêm / Thu gọn nếu có nhiều hơn 6 bản ghi */}
      {safeRecords.length > 6 && (
        <div className="mt-4 pt-3 border-t border-obsidian-border text-center">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-text-muted hover:text-spotify-green transition-colors cursor-pointer py-1.5 px-3 rounded-lg hover:bg-obsidian-bg/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            <span>{isExpanded ? 'Thu gọn danh sách' : `Xem toàn bộ ${safeRecords.length} bài hát gần đây`}</span>
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      )}
    </Card>
  );
};
