import React from 'react';
import { Disc3 } from 'lucide-react';
import type { TopAlbum } from '../../types/analytics';

interface TopAlbumsListProps {
  albums: TopAlbum[];
}

export const TopAlbumsList: React.FC<TopAlbumsListProps> = ({ albums }) => {
  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
              Top Album Nghe Nhiều Nhất
            </h3>
            <p className="text-xs sm:text-sm text-slate-400">
              Những album gắn liền với gu thưởng thức của bạn
            </p>
          </div>
        </div>

        {(!albums || albums.length === 0) ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            Chưa có album nào được ghi nhận trong kỳ này.
          </div>
        ) : (
          <div className="space-y-3">
            {albums.map((album, idx) => (
              <div
                key={album.spotify_id || idx}
                className="flex items-center justify-between p-3 rounded-xl bg-[#0B0F17]/50 border border-[#1E293B]/60 hover:border-[#1DB954]/40 transition-all group"
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <span className="w-5 text-center font-bold text-xs text-slate-500 group-hover:text-[#1DB954]">
                    #{idx + 1}
                  </span>

                  {album.image_url ? (
                    <img
                      src={album.image_url}
                      alt={album.name}
                      className="w-11 h-11 rounded-lg object-cover border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-11 h-11 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <Disc3 className="w-5 h-5" />
                    </div>
                  )}

                  <div className="min-w-0">
                    <h4 className="text-sm font-semibold text-white truncate group-hover:text-[#1DB954] transition-colors">
                      {album.name}
                    </h4>
                    <p className="text-xs text-slate-400 truncate">
                      {album.artists && album.artists.length > 0
                        ? album.artists.join(', ')
                        : 'Nhiều nghệ sĩ'}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0 ml-3">
                  <span className="text-xs font-mono font-bold text-[#1DB954] block">
                    {album.play_count} lượt
                  </span>
                  {album.release_date && (
                    <span className="text-[10px] text-slate-500 block">
                      {album.release_date.slice(0, 4)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
