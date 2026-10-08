import React from 'react';
import { User } from 'lucide-react';
import type { TopArtist } from '../../types/analytics';

interface TopArtistsListProps {
  artists: TopArtist[];
}

export const TopArtistsList: React.FC<TopArtistsListProps> = ({ artists }) => {
  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
            Top Nghệ Sĩ Được Nghe Nhiều Nhất
          </h3>
          <p className="text-xs sm:text-sm text-slate-400">
            Những nghệ sĩ định hình gu thưởng thức âm nhạc của bạn
          </p>
        </div>
      </div>

      {artists.length === 0 ? (
        <div className="py-8 text-center text-slate-500 text-xs">
          Chưa có nghệ sĩ nào được ghi nhận trong kỳ này.
        </div>
      ) : (
        <div className="space-y-3">
          {artists.map((artist, idx) => (
            <div
              key={artist.spotify_id || idx}
              className="flex items-center justify-between p-3 rounded-xl bg-[#0B0F17]/50 border border-[#1E293B]/60 hover:border-[#1DB954]/40 transition-all group"
            >
              <div className="flex items-center space-x-3 min-w-0">
                <span className="w-5 text-center font-bold text-xs text-slate-500 group-hover:text-[#1DB954]">
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
                  <h4 className="text-sm font-semibold text-white truncate group-hover:text-[#1DB954] transition-colors">
                    {artist.name}
                  </h4>
                  <span className="text-[11px] text-slate-500">Nghệ sĩ chính</span>
                </div>
              </div>

              <div className="text-right shrink-0">
                <span className="text-xs font-mono font-bold text-[#1DB954] block">
                  {artist.play_count}
                </span>
                <span className="text-[10px] text-slate-500 uppercase">lượt nghe</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
