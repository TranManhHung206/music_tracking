import React from 'react';
import { Disc3, ExternalLink } from 'lucide-react';
import type { TopAlbum } from '../../types/analytics';
import { isRealSpotifyId } from '../../utils/analyticsFormatters';
import { Card } from '../ui/Card';
import { ListCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface TopAlbumsListProps {
  albums: TopAlbum[];
  periodLabel?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

export const TopAlbumsList: React.FC<TopAlbumsListProps> = ({
  albums = [],
  periodLabel,
  isLoading = false,
  error = null,
  onRetry,
  className = '',
}) => {
  const safeAlbums = Array.isArray(albums) ? albums : [];

  return (
    <Card variant="default" padding="md" className={`flex flex-col ${className}`}>
      <div className="mb-4">
        <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
          Top Album Nghe Nhiều Nhất
        </h3>
        <p className="text-xs sm:text-sm text-text-muted">
          {periodLabel
            ? `Những album gắn liền với gu nghe nhạc (${periodLabel})`
            : 'Những album gắn liền với gu thưởng thức của bạn'}
        </p>
      </div>

      {isLoading ? (
        <ListCardSkeleton rows={5} />
      ) : error ? (
        <SectionErrorState message={error} onRetry={onRetry} />
      ) : safeAlbums.length === 0 ? (
        <SectionEmptyState
          title="Chưa có album nổi bật"
          description="Chưa có album nào được ghi nhận trong kỳ này."
          icon={<Disc3 className="w-5 h-5" />}
          compact
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-3">
          {safeAlbums.map((album, idx) => {
            const spotifyUrl = isRealSpotifyId(album.spotify_id)
              ? `https://open.spotify.com/album/${album.spotify_id}`
              : null;

            return (
              <div
                key={album.spotify_id || idx}
                className="flex items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/70 hover:border-spotify-green/40 transition-all group gap-2"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-5 text-center font-bold text-xs text-text-muted group-hover:text-spotify-green shrink-0">
                    #{idx + 1}
                  </span>

                  {album.image_url ? (
                    <img
                      src={album.image_url}
                      alt={album.name}
                      width={44}
                      height={44}
                      loading="lazy"
                      decoding="async"
                      className="w-11 h-11 rounded-lg object-cover border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <Disc3 className="w-5 h-5" />
                    </div>
                  )}

                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-spotify-green transition-colors">
                      {album.name}
                    </h4>
                    <p className="text-xs text-text-muted truncate">
                      {album.artists && album.artists.length > 0
                        ? album.artists.join(', ')
                        : 'Nhiều nghệ sĩ'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 ml-1">
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-spotify-green block">
                      {album.play_count} lượt
                    </span>
                    {album.release_date && (
                      <span className="text-[11px] text-text-muted block">
                        {album.release_date.slice(0, 4)}
                      </span>
                    )}
                  </div>

                  {spotifyUrl && (
                    <a
                      href={spotifyUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Mở album ${album.name} trên Spotify`}
                      className="min-w-[36px] min-h-[36px] p-2 rounded-lg bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-spotify-green hover:border-spotify-green/50 transition-all flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                      title="Mở album trên Spotify"
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
