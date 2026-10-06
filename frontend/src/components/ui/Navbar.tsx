import React from 'react';
import { Music, RefreshCw, LogOut, CheckCircle, Radio } from 'lucide-react';
import type { UserProfile } from '../../types/auth';

interface NavbarProps {
  user: UserProfile | null;
  isSyncing: boolean;
  onSync: () => void;
  onLogout: () => void;
  onLogin: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  isSyncing,
  onSync,
  onLogout,
  onLogin,
}) => {
  return (
    <header className="w-full bg-[#0B0F17]/90 backdrop-blur-md border-b border-[#1E293B] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/30 flex items-center justify-center text-[#1DB954]">
            <Music className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight text-white flex items-center gap-2">
              MusicTrack <span className="text-xs px-2 py-0.5 rounded bg-[#1DB954]/20 text-[#1DB954] font-medium border border-[#1DB954]/30">AI Insights</span>
            </span>
          </div>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center space-x-4">
          {user ? (
            <>
              {/* Sync Button */}
              <button
                onClick={onSync}
                disabled={isSyncing}
                className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#131B2E] border border-[#1E293B] text-slate-300 hover:text-white hover:border-[#1DB954]/50 transition-all cursor-pointer disabled:opacity-50"
                title="Đồng bộ lịch sử nghe nhạc mới nhất từ Spotify"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-[#1DB954] ${isSyncing ? 'animate-spin' : ''}`} />
                <span>{isSyncing ? 'Đang đồng bộ...' : 'Đồng bộ Spotify'}</span>
              </button>

              {/* Status Badge */}
              <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[11px] bg-emerald-950/60 border border-emerald-800 text-emerald-400">
                <Radio className="w-3 h-3 animate-pulse text-[#1DB954]" />
                <span>Auto-Scrobble 24/7</span>
              </div>

              {/* User Avatar & Name */}
              <div className="flex items-center space-x-3 pl-2 border-l border-[#1E293B]">
                {user.profile_image_url ? (
                  <img
                    src={user.profile_image_url}
                    alt={user.display_name}
                    className="w-8 h-8 rounded-full border border-slate-700 object-cover"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-[#1DB954]/20 border border-[#1DB954]/40 flex items-center justify-center text-xs font-bold text-[#1DB954]">
                    {user.display_name ? user.display_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                )}
                <span className="text-sm font-medium text-slate-200 hidden sm:inline">
                  {user.display_name || user.username}
                </span>

                <button
                  onClick={onLogout}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-[#131B2E] transition-all cursor-pointer"
                  title="Đăng xuất"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <button
              onClick={onLogin}
              className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#1DB954] text-black hover:bg-[#1ED760] transition-all cursor-pointer shadow-lg shadow-[#1DB954]/20"
            >
              <CheckCircle className="w-4 h-4" />
              <span>Kết nối Spotify</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
