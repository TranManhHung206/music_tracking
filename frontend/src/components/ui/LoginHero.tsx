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
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-4xl w-full text-center space-y-8">
        {/* Brand Badge */}
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#1DB954]/10 border border-[#1DB954]/30 text-[#1DB954] text-xs font-semibold tracking-wide">
          <Radio className="w-3.5 h-3.5 animate-pulse" />
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
          <p className="max-w-2xl mx-auto text-sm sm:text-base text-slate-400 leading-relaxed">
            Kết nối tài khoản Spotify để tự động ghi nhận lịch sử nghe nhạc 24/7, phân tích 5 chiều thuộc tính âm thanh và nhận diện hồ sơ tâm lý âm nhạc được tạo bởi mô hình AI hiện đại.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
          <button
            onClick={onLogin}
            disabled={isLoading}
            className="w-full sm:w-auto flex items-center justify-center space-x-3 px-8 py-4 rounded-xl text-sm font-bold bg-[#1DB954] text-black hover:bg-[#1ED760] transition-all transform hover:-translate-y-0.5 shadow-lg shadow-[#1DB954]/25 cursor-pointer disabled:opacity-50"
          >
            <Music className="w-5 h-5" />
            <span>{isLoading ? 'Đang chuyển hướng...' : 'Đăng nhập bằng Spotify'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onEnterDemo}
            className="w-full sm:w-auto flex items-center justify-center space-x-2 px-6 py-4 rounded-xl text-sm font-semibold bg-[#131B2E] border border-[#1E293B] text-slate-300 hover:text-white hover:border-slate-600 transition-all cursor-pointer"
          >
            <Eye className="w-4 h-4 text-slate-400" />
            <span>Xem thử Chế độ Demo (Dữ liệu mẫu)</span>
          </button>
        </div>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-12 text-left">
          <div className="p-5 rounded-2xl bg-[#131B2E]/60 border border-[#1E293B] hover:border-[#1DB954]/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/20 flex items-center justify-center text-[#1DB954] mb-3">
              <Radio className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">Auto-Scrobble 24/7</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Celery Worker ngầm định kỳ thu thập lịch sử nghe nhạc từ Spotify và khử trùng lặp dữ liệu chính xác theo mốc thời gian.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#131B2E]/60 border border-[#1E293B] hover:border-[#1DB954]/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">Trực Quan Hóa Đa Chiều</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Biểu đồ Radar 5 thuộc tính âm thanh (Danceability, Energy...), Heatmap 24x7 và Bar Chart Race đua top nghệ sĩ theo thời gian.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-[#131B2E]/60 border border-[#1E293B] hover:border-[#1DB954]/30 transition-all">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 mb-3">
              <Sparkles className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-white mb-1.5">AI Persona & Gợi Ý KNN</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Mô hình ngôn ngữ lớn phân tích cá tính âm nhạc độc bản kết hợp thuật toán KNN Cosine gợi ý các bài hát tương đồng về chất âm.
            </p>
          </div>
        </div>

        {/* Security Note */}
        <div className="flex items-center justify-center space-x-2 pt-4 text-xs text-slate-500">
          <ShieldCheck className="w-4 h-4 text-emerald-500" />
          <span>Bảo mật chuẩn AES-256 đối xứng: Toàn bộ token Spotify được mã hóa trước khi lưu trữ DB.</span>
        </div>
      </div>
    </div>
  );
};
