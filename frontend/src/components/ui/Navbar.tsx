import React from 'react';
import { Music, RefreshCw, LogOut, CheckCircle, Radio, EyeOff, ShieldAlert } from 'lucide-react';
import type { UserProfile } from '../../types/auth';

interface NavbarProps {
  user: UserProfile | null;
  isDemoMode?: boolean;
  isSyncing: boolean;
  onSync: () => void;
  onLogout: () => void;
  onLogin: () => void;
  onExitDemo?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  isDemoMode = false,
  isSyncing,
  onSync,
  onLogout,
  onLogin,
  onExitDemo,
}) => {
  return (
    <header className="w-full bg-obsidian-bg/90 backdrop-blur-md border-b border-obsidian-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-2.5 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2">
        {/* Brand Logo */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0 shrink-0">
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-spotify-green/10 border border-spotify-green/30 flex items-center justify-center text-spotify-green shrink-0">
            <Music className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div className="min-w-0">
            <span className="font-extrabold text-sm sm:text-lg tracking-tight text-white flex items-center gap-2">
              <span>MusicTrack</span>
              <span className="hidden lg:inline-flex text-xs px-2 py-0.5 rounded bg-spotify-green/20 text-spotify-green font-medium border border-spotify-green/30">
                AI Insights
              </span>
            </span>
          </div>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
          {isDemoMode ? (
            <>
              {/* Demo Mode Badge */}
              <div className="flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-full text-[11px] bg-amber-950/60 border border-amber-800 text-amber-300 font-medium">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0 hidden min-[380px]:block" />
                <span className="sm:hidden">Demo</span>
                <span className="hidden sm:inline md:hidden">Xem thử</span>
                <span className="hidden md:inline">Chế độ Xem thử</span>
              </div>

              {/* Sync Button */}
              <button
                type="button"
                onClick={onSync}
                disabled={isSyncing}
                aria-label="Đồng bộ lịch sử nghe nhạc từ Spotify"
                className="hidden md:inline-flex items-center gap-2 min-h-[36px] px-3 py-1.5 rounded-xl text-xs font-medium bg-obsidian-card border border-obsidian-border text-slate-300 hover:text-white hover:border-spotify-green/50 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                title="Đồng bộ lịch sử nghe nhạc từ Spotify"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-spotify-green ${isSyncing ? 'animate-spin' : ''}`} />
                <span className="lg:hidden">{isSyncing ? 'Đang đồng bộ...' : 'Đồng bộ'}</span>
                <span className="hidden lg:inline">{isSyncing ? 'Đang đồng bộ...' : 'Đồng bộ Spotify'}</span>
              </button>

              {/* Connect Spotify CTA */}
              <button
                type="button"
                onClick={onLogin}
                className="inline-flex items-center gap-1.5 min-h-[34px] sm:min-h-[36px] px-2.5 sm:px-3.5 py-1.5 rounded-xl text-xs font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all cursor-pointer shadow-md shadow-spotify-green/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-bg"
              >
                <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                <span className="min-[380px]:hidden">Spotify</span>
                <span className="hidden min-[380px]:inline sm:hidden">Đăng nhập</span>
                <span className="hidden sm:inline">Đăng nhập Spotify</span>
              </button>

              {/* Exit Demo Button */}
              {onExitDemo && (
                <button
                  type="button"
                  onClick={onExitDemo}
                  aria-label="Thoát chế độ Xem thử"
                  className="min-w-[34px] min-h-[34px] sm:min-w-[36px] sm:min-h-[36px] p-1.5 rounded-xl flex items-center justify-center text-slate-400 hover:text-rose-400 hover:bg-obsidian-card transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                  title="Thoát chế độ Xem thử"
                >
                  <EyeOff className="w-4 h-4" />
                </button>
              )}
            </>
          ) : user ? (
            <>
              {/* Sync Button */}
              <button
                type="button"
                onClick={onSync}
                disabled={isSyncing}
                aria-label="Đồng bộ lịch sử nghe nhạc mới nhất từ Spotify"
                className="inline-flex items-center gap-1.5 sm:gap-2 min-h-[36px] px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-medium bg-obsidian-card border border-obsidian-border text-slate-200 hover:text-white hover:border-spotify-green/50 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                title="Đồng bộ lịch sử nghe nhạc mới nhất từ Spotify"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-spotify-green shrink-0 ${isSyncing ? 'animate-spin' : ''}`} />
                <span className="hidden min-[380px]:inline sm:hidden">{isSyncing ? 'Đồng bộ...' : 'Đồng bộ'}</span>
                <span className="hidden sm:inline">{isSyncing ? 'Đang đồng bộ...' : 'Đồng bộ Spotify'}</span>
              </button>

              {/* Status Badge */}
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] bg-emerald-950/60 border border-emerald-800 text-emerald-300">
                <Radio className="w-3 h-3 animate-pulse text-spotify-green" />
                <span>Auto-Scrobble 24/7</span>
              </div>

              {/* User Avatar & Name */}
              <div className="flex items-center gap-2 pl-2 border-l border-obsidian-border">
                {user.profile_image_url ? (
                  <img
                    src={user.profile_image_url}
                    alt={user.display_name}
                    className="w-8 h-8 rounded-full border border-slate-700 object-cover shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-spotify-green/20 border border-spotify-green/40 flex items-center justify-center text-xs font-bold text-spotify-green shrink-0">
                    {user.display_name ? user.display_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                )}
                <span className="text-sm font-medium text-slate-200 hidden sm:inline max-w-[120px] truncate">
                  {user.display_name || user.username}
                </span>

                <button
                  type="button"
                  onClick={onLogout}
                  aria-label="Đăng xuất khỏi hệ thống"
                  className="min-w-[36px] min-h-[36px] p-1.5 rounded-xl flex items-center justify-center text-slate-400 hover:text-rose-400 hover:bg-obsidian-card transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                  title="Đăng xuất khỏi hệ thống"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <button
              type="button"
              onClick={onLogin}
              className="inline-flex items-center gap-2 min-h-[38px] px-3 sm:px-4 py-2 rounded-xl text-xs font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all cursor-pointer shadow-lg shadow-spotify-green/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-bg"
            >
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span className="sm:hidden">Đăng nhập</span>
              <span className="hidden sm:inline">Đăng nhập bằng Spotify</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
