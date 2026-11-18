import React from 'react';
import { Sparkles, Disc, ExternalLink } from 'lucide-react';
import type { TopTrack } from '../../types/analytics';
import { isRealSpotifyId } from '../../utils/analyticsFormatters';
import { Card } from '../ui/Card';
import { ListCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface TopTracksListProps {
  tracks: TopTrack[];
  onFindSimilar: (trackId: string, trackName: string) => void;
  periodLabel?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const TopTracksList: React.FC<TopTracksListProps> = ({
  tracks = [],
  onFindSimilar,
  periodLabel,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  const safeTracks = Array.isArray(tracks) ? tracks : [];

  return (
    <Card variant="default" padding="md" className="flex flex-col">
      <div className="mb-4">
        <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
          Top Bài Hát Nghe Nhiều Nhất
        </h3>
        <p className="text-xs sm:text-sm text-text-muted">
          {periodLabel
            ? `Các giai điệu đồng hành nhiều nhất (${periodLabel})`
            : 'Các giai điệu đồng hành cùng bạn nhiều nhất trong kỳ'}
        </p>
      </div>

      {isLoading ? (
        <ListCardSkeleton rows={5} />
      ) : error ? (
        <SectionErrorState message={error} onRetry={onRetry} />
      ) : safeTracks.length === 0 ? (
        <SectionEmptyState
          title="Chưa có bài hát nổi bật"
          description="Chưa có lượt phát bài hát nào được ghi nhận trong kỳ này."
          icon={<Disc className="w-5 h-5" />}
          compact
        />
      ) : (
        <div className="space-y-3">
          {safeTracks.map((track, idx) => {
            const spotifyUrl = isRealSpotifyId(track.spotify_id)
              ? `https://open.spotify.com/track/${track.spotify_id}`
              : null;

            return (
              <div
                key={track.spotify_id || idx}
                className="flex items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/70 hover:border-spotify-green/40 transition-all group gap-2"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-5 text-center font-bold text-xs text-text-muted group-hover:text-spotify-green shrink-0">
                    #{idx + 1}
                  </span>

                  {track.album_image_url ? (
                    <img
                      src={track.album_image_url}
                      alt={track.name}
                      width={44}
                      height={44}
                      loading="lazy"
                      decoding="async"
                      className="w-11 h-11 rounded-lg object-cover border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <Disc className="w-5 h-5" />
                    </div>
                  )}

                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-spotify-green transition-colors leading-5">
                      {track.name}
                    </h4>
                    <p className="text-xs text-text-muted truncate leading-4 mt-0.5">
                      {Array.isArray(track.artists) ? track.artists.join(', ') : ''}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
                  <div className="text-right mr-0.5">
                    <span className="text-xs font-mono font-bold text-spotify-green block leading-5">
                      {track.play_count}
                    </span>
                    <span className="text-[11px] text-text-muted block leading-4">lượt</span>
                  </div>

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
                    onClick={() => onFindSimilar(track.spotify_id, track.name)}
                    aria-label={`Tìm bài hát tương đồng với ${track.name}`}
                    className="min-w-[36px] min-h-[36px] p-2 rounded-lg bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-spotify-green hover:border-spotify-green/50 transition-all cursor-pointer flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                    title="Gợi ý bài hát tương đồng bằng AI"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
