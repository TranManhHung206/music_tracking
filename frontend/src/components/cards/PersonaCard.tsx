import React from 'react';
import { Sparkles, Share2, Compass, RefreshCw, Clock } from 'lucide-react';
import { isValidPersona, type AIMusicPersona } from '../../types/ai';
import { Card } from '../ui/Card';
import { PersonaCardSkeleton } from '../ui/Skeleton';
import { SectionErrorState } from '../ui/SectionState';

interface PersonaCardProps {
  persona: AIMusicPersona | null;
  isLoading?: boolean;
  isGenerating: boolean;
  error?: string | null;
  onRegenerate: () => void;
  onRetry?: () => void;
  onOpenShareModal: () => void;
  cooldownSeconds?: number;
}

function getProviderLabel(providerUsed?: string): string {
  if (!providerUsed) return 'AI Music Persona';
  const lower = providerUsed.toLowerCase();
  if (lower.includes('backup') || lower.includes('20b')) return 'Groq 20B Backup';
  if (lower.includes('groq')) return 'Groq LPU';
  if (lower.includes('gemini')) return 'Google Gemini';
  if (lower.includes('heuristic')) return 'Phân tích nội bộ';
  return providerUsed;
}

export const PersonaCard: React.FC<PersonaCardProps> = ({
  persona,
  isLoading = false,
  isGenerating,
  error = null,
  onRegenerate,
  onRetry,
  onOpenShareModal,
  cooldownSeconds = 0,
}) => {
  if (isLoading && !persona) {
    return (
      <Card variant="ai" padding="lg" className="rounded-3xl">
        <PersonaCardSkeleton />
      </Card>
    );
  }

  if (error && !persona) {
    return (
      <Card variant="ai" padding="lg" className="rounded-3xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-bold text-white">AI Music Persona</h2>
        </div>
        <SectionErrorState message={error} onRetry={onRetry} />
      </Card>
    );
  }

  if (!isValidPersona(persona)) {
    return (
      <Card variant="ai" padding="lg" className="rounded-3xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          <div className="flex items-start gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400 block">
                AI Music Persona
              </span>
              <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                Bạn chưa tạo hồ sơ Cá tính Âm nhạc AI
              </h2>
              <p className="text-xs sm:text-sm text-text-muted max-w-2xl leading-relaxed">
                Nhấn nút bên cạnh để AI phân tích thói quen nghe nhạc 30 ngày gần nhất, đặc trưng âm thanh và khung giờ vàng của riêng bạn.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onRegenerate}
            disabled={isGenerating || cooldownSeconds > 0}
            className="shrink-0 min-h-[40px] inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-[#1DB954] text-white hover:brightness-110 transition-all cursor-pointer disabled:opacity-50 shadow-lg shadow-purple-900/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            <span>
              {cooldownSeconds > 0
                ? `Chờ ${cooldownSeconds}s`
                : isGenerating
                ? 'Đang phân tích...'
                : 'Khám phá Cá tính AI'}
            </span>
          </button>
        </div>
      </Card>
    );
  }

  const moodEntries = Object.entries(persona.mood_distribution || {});

  return (
    <Card
      variant="ai"
      padding="lg"
      className="rounded-3xl hover:border-purple-500/40 relative overflow-hidden duration-300"
    >
      {/* Background Neon Glow */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-spotify-green/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 sm:pb-6 border-b border-obsidian-border gap-4 relative z-10">
        <div className="flex items-start sm:items-center gap-3 min-w-0">
          <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 shadow-inner shrink-0">
            <Sparkles className="w-5 h-5 sm:w-6 sm:h-6" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                AI Music Persona
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-200 border border-slate-700 font-mono">
                {getProviderLabel(persona.provider_used)}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-obsidian-bg text-text-muted border border-slate-800">
                Cửa sổ: 30 ngày gần nhất
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight mt-1 break-words">
              {persona.persona_title}
            </h2>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={isGenerating || cooldownSeconds > 0}
            className="min-h-[38px] flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-obsidian-bg border border-obsidian-border text-slate-200 hover:text-white hover:border-purple-500/50 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
            title={cooldownSeconds > 0 ? `Vui lòng chờ ${cooldownSeconds}s` : 'Phân tích lại cá tính AI'}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin text-purple-400' : ''}`} />
            <span>
              {cooldownSeconds > 0 ? `Chờ ${cooldownSeconds}s` : isGenerating ? 'Đang phân tích...' : 'Phân tích lại'}
            </span>
          </button>

          <button
            type="button"
            onClick={onOpenShareModal}
            className="min-h-[38px] flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 to-[#1DB954] text-white hover:brightness-110 transition-all cursor-pointer shadow-lg shadow-purple-900/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Xuất thẻ chia sẻ</span>
          </button>
        </div>
      </div>

      {/* Tagline */}
      {persona.tagline && (
        <div className="py-4 relative z-10">
          <p className="text-sm sm:text-base font-medium italic text-emerald-300/90">
            "{persona.tagline}"
          </p>
        </div>
      )}

      {/* Vibe Summary */}
      {persona.vibe_summary && (
        <div className="bg-obsidian-bg/70 border border-obsidian-border rounded-2xl p-4 sm:p-5 mb-6 relative z-10 text-xs sm:text-sm text-slate-200 leading-relaxed">
          {persona.vibe_summary}
        </div>
      )}

      {/* Mood Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted mb-3 flex items-center gap-1.5">
            <Compass className="w-4 h-4 text-spotify-green" />
            <span>Phân Bổ Cảm Xúc Âm Nhạc</span>
          </h4>
          <div className="space-y-2.5">
            {moodEntries.map(([mood, pct]) => (
              <div key={mood}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="capitalize text-slate-200 font-medium">{mood}</span>
                  <span className="font-mono text-purple-300 font-bold">{pct}%</span>
                </div>
                <div className="w-full bg-obsidian-bg rounded-full h-2 overflow-hidden border border-obsidian-border">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-[#1DB954] rounded-full"
                    style={{ width: `${Math.min(Math.max(Number(pct) || 0, 0), 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Advice & Recommended Time */}
        <div className="space-y-4 flex flex-col justify-between">
          {persona.recommended_listening_time && (
            <div className="bg-obsidian-bg/55 border border-obsidian-border rounded-xl p-3.5 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-spotify-green shrink-0">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[11px] text-text-muted block">Khung giờ nghe lý tưởng</span>
                <span className="text-xs font-bold text-white">{persona.recommended_listening_time}</span>
              </div>
            </div>
          )}

          {persona.ai_advice && (
            <div className="bg-purple-950/25 border border-purple-800/35 rounded-xl p-4">
              <span className="text-[11px] font-bold text-purple-300 uppercase tracking-wider block mb-1">
                Lời Khuyên Từ Chuyên Gia Aura
              </span>
              <p className="text-xs text-slate-200 leading-normal">{persona.ai_advice}</p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
