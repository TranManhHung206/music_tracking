import React, { useState } from 'react';
import { History, Clock, Sparkles, Disc, ExternalLink, RotateCw, ChevronDown, ChevronUp } from 'lucide-react';
import type { ListeningHistoryRecord } from '../../types/analytics';

interface RecentScrobblesListProps {
  records: ListeningHistoryRecord[];
  isLoading?: boolean;
  onRefresh?: () => void;
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
  onRefresh,
  onFindSimilar,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const safeRecords = Array.isArray(records) ? records.filter((r) => r && r.track) : [];
  const displayLimit = isExpanded ? safeRecords.length : 6;
  const visibleRecords = safeRecords.slice(0, displayLimit);

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-[#1E293B]">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/20 flex items-center justify-center text-[#1DB954] shrink-0">
            <History className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                Nhật Ký Nghe Nhạc Gần Đây
              </h3>
              <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/20">
                Auto-Scrobble
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Các bản nhạc được đồng bộ tự động theo thời gian thực từ Spotify
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-[#0B0F17] border border-[#1E293B] text-xs text-slate-300 hover:text-white hover:border-[#1DB954]/50 transition-all cursor-pointer disabled:opacity-50"
              title="Làm mới lịch sử nghe nhạc"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[#1DB954]' : ''}`} />
              <span className="hidden md:inline">Làm mới</span>
            </button>
          )}
        </div>
      </div>

      {/* Danh sach bai hat */}
      {safeRecords.length === 0 ? (
        <div className="py-12 text-center text-slate-500 text-xs">
          Chưa có lượt nghe nào được ghi nhận. Hãy mở Spotify thưởng thức âm nhạc để kích hoạt Auto-Scrobble.
        </div>
      ) : (
        <div className="space-y-2.5">
          {visibleRecords.map((item, idx) => {
            const track = item?.track;
            if (!track) return null;

            const albumImage = track.album?.image_url;
            const artistsText = Array.isArray(track.artists)
              ? track.artists.map((a) => a?.name).filter(Boolean).join(', ')
              : 'Nghệ sĩ chưa rõ';
            const spotifyUrl = track.spotify_id && !track.spotify_id.startsWith('mock')
              ? `https://open.spotify.com/track/${track.spotify_id}`
              : null;
            const durationMs = typeof track.duration_ms === 'number' ? track.duration_ms : 0;

            return (
              <div
                key={item.id || idx}
                className="flex items-center justify-between p-3 rounded-xl bg-[#0B0F17]/50 border border-[#1E293B]/60 hover:border-[#1DB954]/40 hover:bg-[#0B0F17]/80 transition-all group"
              >
                {/* Ben trai: Anh album + Thong tin bai hat */}
                <div className="flex items-center space-x-3 min-w-0 mr-3">
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
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-[#1DB954] transition-colors">
                      {track.name}
                    </h4>
                    <p className="text-xs text-slate-400 truncate">
                      {artistsText}
                      {track.album?.name ? ` • ${track.album.name}` : ''}
                    </p>
                  </div>
                </div>

                {/* Ben phai: Thoi gian nghe + Thoi luong + Action buttons */}
                <div className="flex items-center space-x-3 shrink-0">
                  <div className="text-right hidden sm:block">
                    <div className="flex items-center justify-end space-x-1 text-xs font-medium text-slate-300">
                      <Clock className="w-3 h-3 text-[#1DB954]" />
                      <span>{formatRelativeTime(item.played_at)}</span>
                    </div>
                    {durationMs > 0 && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        {formatDuration(durationMs)}
                      </span>
                    )}
                  </div>

                  <span className="sm:hidden text-[11px] text-slate-400 font-medium">
                    {formatRelativeTime(item.played_at)}
                  </span>

                  <div className="flex items-center space-x-1.5">
                    {spotifyUrl && (
                      <a
                        href={spotifyUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 rounded-lg bg-[#131B2E] border border-[#1E293B] text-slate-400 hover:text-[#1DB954] hover:border-[#1DB954]/50 transition-all"
                        title="Mở trên Spotify"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}

                    <button
                      onClick={() => onFindSimilar(track.spotify_id || '', track.name || '')}
                      className="p-2 rounded-lg bg-[#131B2E] border border-[#1E293B] text-slate-400 hover:text-[#1DB954] hover:border-[#1DB954]/50 transition-all cursor-pointer"
                      title="Gợi ý bài hát tương đồng bằng AI KNN"
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

      {/* Nut Xem them / Thu gon neu co nhieu hon 6 ban ghi */}
      {records.length > 6 && (
        <div className="mt-4 pt-3 border-t border-[#1E293B] text-center">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-[#1DB954] transition-colors cursor-pointer py-1 px-3 rounded-lg hover:bg-[#0B0F17]/50"
          >
            <span>{isExpanded ? 'Thu gọn danh sách' : `Xem toàn bộ ${records.length} bài hát gần đây`}</span>
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      )}
    </div>
  );
};
