import React from 'react';
import { Sparkles, Share2, Compass, RefreshCw, Clock } from 'lucide-react';
import type { AIMusicPersona } from '../../types/ai';

interface PersonaCardProps {
  persona: AIMusicPersona;
  isGenerating: boolean;
  onRegenerate: () => void;
  onOpenShareModal: () => void;
}

export const PersonaCard: React.FC<PersonaCardProps> = ({
  persona,
  isGenerating,
  onRegenerate,
  onOpenShareModal,
}) => {
  return (
    <div className="w-full bg-gradient-to-br from-[#131B2E] via-[#0F172A] to-[#131B2E] border border-purple-900/30 hover:border-purple-500/40 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden transition-all duration-300">
      {/* Background Neon Glow */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-[#1DB954]/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[#1E293B] gap-4 relative z-10">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-inner">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                AI Music Persona
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                {persona.provider_used || 'Groq GPT-OSS-120B'}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight mt-0.5">
              {persona.persona_title}
            </h2>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onRegenerate}
            disabled={isGenerating}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#0B0F17] border border-[#1E293B] text-slate-300 hover:text-white hover:border-purple-500/50 transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin text-purple-400' : ''}`} />
            <span>{isGenerating ? 'Đang phân tích...' : 'Phân tích lại'}</span>
          </button>

          <button
            onClick={onOpenShareModal}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-[#1DB954] text-white hover:brightness-110 transition-all cursor-pointer shadow-lg shadow-purple-900/20"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Xuất thẻ chia sẻ</span>
          </button>
        </div>
      </div>

      {/* Tagline */}
      <div className="py-4 relative z-10">
        <p className="text-sm sm:text-base font-medium italic text-emerald-300/90">
          "{persona.tagline}"
        </p>
      </div>

      {/* Vibe Summary */}
      <div className="bg-[#0B0F17]/70 border border-[#1E293B] rounded-2xl p-5 mb-6 relative z-10 text-xs sm:text-sm text-slate-300 leading-relaxed">
        {persona.vibe_summary}
      </div>

      {/* Mood Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
            <Compass className="w-4 h-4 text-[#1DB954]" />
            <span>Phân Bổ Cảm Xúc Âm Nhạc</span>
          </h4>
          <div className="space-y-2.5">
            {Object.entries(persona.mood_distribution).map(([mood, pct]) => (
              <div key={mood}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="capitalize text-slate-300 font-medium">{mood}</span>
                  <span className="font-mono text-purple-400 font-bold">{pct}%</span>
                </div>
                <div className="w-full bg-[#0B0F17] rounded-full h-2 overflow-hidden border border-[#1E293B]">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-[#1DB954] rounded-full"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Advice & Recommended Time */}
        <div className="space-y-4 flex flex-col justify-between">
          {persona.recommended_listening_time && (
            <div className="bg-[#0B0F17]/50 border border-[#1E293B] rounded-xl p-3.5 flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-[#1DB954]">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Khung giờ nghe lý tưởng</span>
                <span className="text-xs font-bold text-white">{persona.recommended_listening_time}</span>
              </div>
            </div>
          )}

          <div className="bg-purple-950/20 border border-purple-800/30 rounded-xl p-4">
            <span className="text-[11px] font-bold text-purple-400 uppercase tracking-wider block mb-1">
              Lời Khuyên Từ Chuyên Gia Aura
            </span>
            <p className="text-xs text-slate-300 leading-normal">
              {persona.ai_advice}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
