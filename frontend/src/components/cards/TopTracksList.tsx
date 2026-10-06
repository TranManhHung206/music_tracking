import React from 'react';
import { Sparkles, Disc } from 'lucide-react';
import type { TopTrack } from '../../types/analytics';

interface TopTracksListProps {
  tracks: TopTrack[];
  onFindSimilar: (trackId: string, trackName: string) => void;
}

export const TopTracksList: React.FC<TopTracksListProps> = ({ tracks, onFindSimilar }) => {
  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            Top Bài Hát Nghe Nhiều Nhất
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Các giai điệu đồng hành cùng bạn nhiều nhất trong kỳ
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {tracks.map((track, idx) => (
          <div
            key={track.spotify_id || idx}
            className="flex items-center justify-between p-3 rounded-xl bg-[#0B0F17]/50 border border-[#1E293B]/60 hover:border-[#1DB954]/40 transition-all group"
          >
            <div className="flex items-center space-x-3 min-w-0">
              <span className="w-5 text-center font-bold text-xs text-slate-500 group-hover:text-[#1DB954]">
                #{idx + 1}
              </span>

              {track.album_image_url ? (
                <img
                  src={track.album_image_url}
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
                  {track.artists.join(', ')}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3 shrink-0 ml-2">
              <div className="text-right">
                <span className="text-xs font-mono font-bold text-white block">
                  {track.play_count}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">lượt nghe</span>
              </div>

              <button
                onClick={() => onFindSimilar(track.spotify_id, track.name)}
                className="p-2 rounded-lg bg-[#131B2E] border border-[#1E293B] text-slate-400 hover:text-[#1DB954] hover:border-[#1DB954]/50 transition-all cursor-pointer"
                title="Gợi ý bài hát tương đồng bằng AI KNN"
              >
                <Sparkles className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
