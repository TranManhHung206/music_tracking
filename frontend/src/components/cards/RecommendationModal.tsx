import React from 'react';
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
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#131B2E] border border-[#1E293B] w-full max-w-xl rounded-2xl p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#1E293B]">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/30 flex items-center justify-center text-[#1DB954]">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Gợi Ý Bài Hát Tương Đồng</h3>
              <p className="text-xs text-slate-400">Thuật toán Scikit-Learn KNN Cosine Distance</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#0B0F17] transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-[#1DB954] border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-400">Đang quét không gian vector 5D tìm bài tương đồng...</p>
          </div>
        ) : data ? (
          <div className="pt-4 space-y-4">
            {/* Seed Track Info */}
            <div className="p-3.5 rounded-xl bg-[#0B0F17] border border-[#1E293B] flex items-center space-x-3">
              {data.seed_track.image_url ? (
                <img
                  src={data.seed_track.image_url}
                  alt={data.seed_track.name}
                  className="w-12 h-12 rounded-lg object-cover"
                />
              ) : (
                <div className="w-12 h-12 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
                  <Disc className="w-6 h-6" />
                </div>
              )}
              <div>
                <span className="text-[10px] uppercase font-bold text-[#1DB954] tracking-wider block">
                  Bài Hát Gốc (Seed Track)
                </span>
                <h4 className="text-sm font-bold text-white">{data.seed_track.name}</h4>
                <p className="text-xs text-slate-400">{data.seed_track.artists.join(', ')}</p>
              </div>
            </div>

            {/* Recommendations List */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                Top Đề Xuất Phù Hợp Vibe
              </span>
              {data.recommendations.length > 0 ? (
                data.recommendations.map((rec, idx) => (
                  <div
                    key={rec.spotify_id || idx}
                    className="flex items-center justify-between p-3 rounded-xl bg-[#0B0F17]/50 border border-[#1E293B]/70 hover:border-[#1DB954]/50 transition-all"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <span className="text-xs font-bold text-slate-500 w-4 text-center">
                        #{idx + 1}
                      </span>
                      {rec.image_url ? (
                        <img
                          src={rec.image_url}
                          alt={rec.name}
                          className="w-10 h-10 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
                          <Disc className="w-4 h-4" />
                        </div>
                      )}
                      <div className="min-w-0">
                        <h5 className="text-xs sm:text-sm font-semibold text-white truncate">
                          {rec.name}
                        </h5>
                        <p className="text-[11px] text-slate-400 truncate">
                          {rec.artists.join(', ')}
                        </p>
                      </div>
                    </div>

                    <div className="text-right ml-2 shrink-0">
                      <span className="text-xs font-mono font-bold text-[#1DB954]">
                        {(rec.similarity_score * 100).toFixed(0)}%
                      </span>
                      <span className="text-[10px] text-slate-500 block">tương đồng</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic py-4 text-center">
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
