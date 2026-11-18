import React, { useEffect } from 'react';
import { X, Sparkles, Disc } from 'lucide-react';
import type { RecommendationResult } from '../../types/ai';

interface RecommendationModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: RecommendationResult | null;
  isLoading: boolean;
}

export const RecommendationModal: React.FC<RecommendationModalProps> = ({
  isOpen,
  onClose,
  data,
  isLoading,
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="rec-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-obsidian-card border border-obsidian-border w-full max-w-xl rounded-2xl p-4 sm:p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto scrollbar-thin">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-obsidian-border gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-spotify-green/10 border border-spotify-green/30 flex items-center justify-center text-spotify-green shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 id="rec-modal-title" className="text-base font-bold text-white truncate">
                Gợi Ý Bài Hát Tương Đồng
              </h3>
              <p className="text-xs text-text-muted truncate">
                Đề xuất theo 5 đặc trưng chất âm của bài hát gốc
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng hộp thoại gợi ý bài hát"
            className="min-w-[36px] min-h-[36px] p-1.5 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-obsidian-bg transition-all cursor-pointer shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-text-muted">Đang tìm các bản nhạc có sắc thái tương đồng...</p>
          </div>
        ) : data ? (
          <div className="pt-4 space-y-4">
            {/* Seed Track Info */}
            <div className="p-3.5 rounded-xl bg-obsidian-bg border border-obsidian-border flex items-center gap-3">
              {data.seed_track.image_url ? (
                <img
                  src={data.seed_track.image_url}
                  alt={data.seed_track.name}
                  width={48}
                  height={48}
                  decoding="async"
                  className="w-12 h-12 rounded-lg object-cover shrink-0"
                />
              ) : (
                <div className="w-12 h-12 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                  <Disc className="w-6 h-6" />
                </div>
              )}
              <div className="min-w-0">
                <span className="text-[11px] uppercase font-bold text-spotify-green tracking-wider block">
                  Bài hát gốc
                </span>
                <h4 className="text-sm font-bold text-white truncate">{data.seed_track.name}</h4>
                <p className="text-xs text-text-muted truncate">{data.seed_track.artists.join(', ')}</p>
              </div>
            </div>

            {/* Recommendations List */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block">
                Top Đề Xuất Phù Hợp Vibe
              </span>
              {data.recommendations.length > 0 ? (
                data.recommendations.map((rec, idx) => (
                  <div
                    key={rec.spotify_id || idx}
                    className="flex items-center justify-between p-3 rounded-xl bg-obsidian-bg/50 border border-obsidian-border/70 hover:border-spotify-green/50 transition-all gap-2"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xs font-bold text-text-muted w-5 text-center shrink-0">
                        #{idx + 1}
                      </span>
                      {rec.image_url ? (
                        <img
                          src={rec.image_url}
                          alt={rec.name}
                          width={40}
                          height={40}
                          loading="lazy"
                          decoding="async"
                          className="w-10 h-10 rounded-lg object-cover shrink-0"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                          <Disc className="w-4 h-4" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <h5 className="text-xs sm:text-sm font-semibold text-white truncate">
                          {rec.name}
                        </h5>
                        <p className="text-[11px] text-text-muted truncate">
                          {rec.artists.join(', ')}
                        </p>
                      </div>
                    </div>

                    <div className="text-right ml-2 shrink-0">
                      <span className="text-xs font-mono font-bold text-spotify-green">
                        {(rec.similarity_score * 100).toFixed(0)}%
                      </span>
                      <span className="text-[11px] text-text-muted block">tương đồng</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-text-muted py-4 text-center">
                  Chưa có thêm bài hát đủ điều kiện tương đồng trong thư viện.
                </p>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};
