import React from 'react';
import { User, ExternalLink } from 'lucide-react';
import type { TopArtist } from '../../types/analytics';
import { isRealSpotifyId } from '../../utils/analyticsFormatters';
import { Card } from '../ui/Card';
import { ListCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface TopArtistsListProps {
  artists: TopArtist[];
  periodLabel?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const TopArtistsList: React.FC<TopArtistsListProps> = ({
  artists = [],
  periodLabel,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  const safeArtists = Array.isArray(artists) ? artists : [];

  return (
    <Card variant="default" padding="md" className="flex flex-col">
      <div className="mb-4">
        <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
          Top Nghệ Sĩ Được Nghe Nhiều Nhất
        </h3>
        <p className="text-xs sm:text-sm text-text-muted">
          {periodLabel
            ? `Những nghệ sĩ định hình gu nghe nhạc (${periodLabel})`
            : 'Những nghệ sĩ định hình gu thưởng thức âm nhạc của bạn'}
        </p>
      </div>

      {isLoading ? (
        <ListCardSkeleton rows={5} />
      ) : error ? (
        <SectionErrorState message={error} onRetry={onRetry} />
      ) : safeArtists.length === 0 ? (
        <SectionEmptyState
          title="Chưa có nghệ sĩ nổi bật"
          description="Chưa có nghệ sĩ nào được ghi nhận trong kỳ này."
          icon={<User className="w-5 h-5" />}
          compact
        />
      ) : (
        <div className="space-y-3">
          {safeArtists.map((artist, idx) => {
            const spotifyUrl = isRealSpotifyId(artist.spotify_id)
              ? `https://open.spotify.com/artist/${artist.spotify_id}`
              : null;

            return (
              <div
                key={artist.spotify_id || idx}
                className="flex items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/70 hover:border-spotify-green/40 transition-all group gap-2"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-5 text-center font-bold text-xs text-text-muted group-hover:text-spotify-green shrink-0">
                    #{idx + 1}
                  </span>

                  {artist.image_url ? (
                    <img
                      src={artist.image_url}
                      alt={artist.name}
                      className="w-11 h-11 rounded-full object-cover border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <User className="w-5 h-5" />
                    </div>
                  )}

                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-spotify-green transition-colors leading-5">
                      {artist.name}
                    </h4>
                    <span className="text-[11px] text-text-muted block leading-4 mt-0.5">Nghệ sĩ chính</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-spotify-green block leading-5">
                      {artist.play_count}
                    </span>
                    <span className="text-[11px] text-text-muted block leading-4">lượt</span>
                  </div>

                  {spotifyUrl && (
                    <a
                      href={spotifyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Mở nghệ sĩ ${artist.name} trên Spotify`}
                      className="min-w-[36px] min-h-[36px] p-2 rounded-lg bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-spotify-green hover:border-spotify-green/50 transition-all flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                      title="Mở trang nghệ sĩ trên Spotify"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
