import React from 'react';
import {
  Music,
  Radio,
  BarChart3,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Eye,
} from 'lucide-react';

interface LoginHeroProps {
  onLogin: () => void;
  onEnterDemo: () => void;
  isLoading?: boolean;
}

export const LoginHero: React.FC<LoginHeroProps> = ({
  onLogin,
  onEnterDemo,
  isLoading = false,
}) => {
  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-10 sm:py-12 sm:px-6 lg:px-8">
      <div className="max-w-4xl w-full text-center space-y-8">
        {/* Brand Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-spotify-green/10 border border-spotify-green/30 text-spotify-green text-xs font-semibold tracking-wide">
          <Radio className="w-3.5 h-3.5 animate-pulse shrink-0" />
          <span>Hệ thống Phân Tích Dữ Liệu Âm Nhạc & Trí Tuệ Nhân Tạo</span>
        </div>

        {/* Main Title & Description */}
        <div className="space-y-4">
          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            Khám Phá Thế Giới Âm Nhạc & <br className="hidden sm:inline" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#1DB954] via-emerald-400 to-teal-300">
              Cá Tính AI Persona Của Bạn
            </span>
          </h1>
          <p className="max-w-2xl mx-auto text-sm sm:text-base text-text-muted leading-relaxed">
            Kết nối tài khoản Spotify để tự động ghi nhận lịch sử nghe nhạc 24/7, phân tích 5 chiều thuộc tính âm thanh và nhận diện hồ sơ tâm lý âm nhạc được tạo bởi AI.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4 pt-2">
          <button
            type="button"
            onClick={onLogin}
            disabled={isLoading}
            className="w-full sm:w-auto min-h-[48px] flex items-center justify-center gap-3 px-7 py-3.5 rounded-xl text-sm font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all transform hover:-translate-y-0.5 shadow-lg shadow-spotify-green/25 cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-bg"
          >
            <Music className="w-5 h-5 shrink-0" />
            <span>{isLoading ? 'Đang chuyển hướng...' : 'Đăng nhập bằng Spotify'}</span>
            <ArrowRight className="w-4 h-4 shrink-0" />
          </button>

          <button
            type="button"
            onClick={onEnterDemo}
            className="w-full sm:w-auto min-h-[48px] flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold bg-obsidian-card border border-obsidian-border text-slate-200 hover:text-white hover:border-slate-600 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-bg"
          >
            <Eye className="w-4 h-4 text-slate-400 shrink-0" />
            <span>Xem thử Chế độ Demo (Dữ liệu mẫu)</span>
          </button>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-8 sm:pt-12 text-left">
          <div className="p-5 rounded-2xl bg-obsidian-card/70 border border-obsidian-border hover:border-spotify-green/35 transition-all">
            <div className="w-10 h-10 rounded-xl bg-spotify-green/10 border border-spotify-green/20 flex items-center justify-center text-spotify-green mb-3">
              <Radio className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">Auto-Scrobble 24/7</h2>
            <p className="text-xs text-text-muted leading-relaxed">
              Tự động đồng bộ định kỳ lịch sử nghe nhạc từ Spotify và khử trùng lặp chính xác theo từng mốc thời gian phát.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-obsidian-card/70 border border-obsidian-border hover:border-spotify-green/35 transition-all">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">Trực Quan Hóa Đa Chiều</h2>
            <p className="text-xs text-text-muted leading-relaxed">
              Biểu đồ Radar 5 chiều âm thanh, bản đồ mật độ nghe theo Tuần, Tháng, Năm và biểu đồ so sánh xu hướng thích ứng.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-obsidian-card/70 border border-obsidian-border hover:border-spotify-green/35 transition-all">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-3">
              <Sparkles className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">AI Persona & Gợi Ý Nhạc</h2>
            <p className="text-xs text-text-muted leading-relaxed">
              Phân tích cá tính thưởng thức âm nhạc độc bản, điều tra thói quen nghe đặc biệt và gợi ý bài hát tương đồng về chất âm.
            </p>
          </div>
        </div>

        {/* Security Note */}
        <div className="flex items-center justify-center gap-2 pt-2 text-xs text-text-muted">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Dữ liệu xác thực Spotify được mã hóa bảo mật trước khi lưu trữ.</span>
        </div>
      </div>
    </div>
  );
};
