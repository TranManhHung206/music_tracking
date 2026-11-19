import React, { useState } from 'react';
import { Search, RotateCw, Sparkles, Repeat, Moon, Trophy, Zap, Clock, ShieldCheck } from 'lucide-react';
import type { MusicFact, AgentMeta } from '../../types/ai';
import { Card } from '../ui/Card';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

interface MusicFactsSectionProps {
  facts?: MusicFact[];
  agentMeta?: AgentMeta;
  periodLabel?: string;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onRetry?: () => void;
  cooldownSeconds?: number;
}

export const MusicFactsSection: React.FC<MusicFactsSectionProps> = ({
  facts = [],
  agentMeta,
  periodLabel = 'Kỳ này',
  isLoading = false,
  error = null,
  onRefresh,
  onRetry,
  cooldownSeconds = 0,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefreshClick = async () => {
    if (onRefresh && !isLoading && !isRefreshing && cooldownSeconds <= 0) {
      setIsRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setIsRefreshing(false);
      }
    }
  };

  const getCategoryTheme = (category: string) => {
    switch (category) {
      case 'repeat_loop':
        return {
          badgeBg: 'bg-pink-500/10 text-pink-300 border-pink-500/25',
          borderColor: 'border-pink-500/20 hover:border-pink-500/40',
          glowBg: 'bg-pink-500/5',
          icon: <Repeat className="w-3.5 h-3.5 text-pink-400 shrink-0" />,
        };
      case 'night_owl':
        return {
          badgeBg: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/25',
          borderColor: 'border-indigo-500/20 hover:border-indigo-500/40',
          glowBg: 'bg-indigo-500/5',
          icon: <Moon className="w-3.5 h-3.5 text-indigo-400 shrink-0" />,
        };
      case 'artist_dominance':
        return {
          badgeBg: 'bg-spotify-green/10 text-spotify-green border-spotify-green/25',
          borderColor: 'border-spotify-green/20 hover:border-spotify-green/40',
          glowBg: 'bg-spotify-green/5',
          icon: <Trophy className="w-3.5 h-3.5 text-spotify-green shrink-0" />,
        };
      case 'marathon':
        return {
          badgeBg: 'bg-amber-500/10 text-amber-300 border-amber-500/25',
          borderColor: 'border-amber-500/20 hover:border-amber-500/40',
          glowBg: 'bg-amber-500/5',
          icon: <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0" />,
        };
      case 'contrast':
        return {
          badgeBg: 'bg-teal-500/10 text-teal-300 border-teal-500/25',
          borderColor: 'border-teal-500/20 hover:border-teal-500/40',
          glowBg: 'bg-teal-500/5',
          icon: <Zap className="w-3.5 h-3.5 text-teal-400 shrink-0" />,
        };
      default:
        return {
          badgeBg: 'bg-purple-500/10 text-purple-300 border-purple-500/25',
          borderColor: 'border-purple-500/20 hover:border-purple-500/40',
          glowBg: 'bg-purple-500/5',
          icon: <Sparkles className="w-3.5 h-3.5 text-purple-400 shrink-0" />,
        };
    }
  };

  const isPreview = agentMeta?.provider_used === 'db-analytics-preview';
  const safeFacts = Array.isArray(facts) ? facts : [];

  return (
    <Card variant="default" padding="md" className="rounded-3xl sm:p-6 shadow-2xl relative overflow-hidden">
      {/* Background Neon Subtle Glow */}
      <div className="absolute top-0 right-1/4 w-72 h-72 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-72 h-72 bg-spotify-green/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-800/80 gap-3 z-10 relative">
        <div className="flex items-start sm:items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-2xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 shrink-0 shadow-lg shadow-purple-500/10">
            <Search className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                AI Music Detective
              </h3>
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/25">
                Agentic AI
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-obsidian-bg text-text-muted border border-slate-800">
                Phạm vi: {periodLabel}
              </span>
            </div>
            <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
              {isPreview
                ? `Thống kê nhanh (${periodLabel}). Nhấn nút để kích hoạt Thám tử AI điều tra chuyên sâu.`
                : `AI điều tra thói quen nghe nhạc thực tế (${periodLabel})`}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {agentMeta && (
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-obsidian-bg/60 border border-slate-800 text-[11px] text-text-muted">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>
                {agentMeta.provider_used.includes('backup')
                  ? `${agentMeta.model_name || 'Backup Model'} (Dự phòng)`
                  : agentMeta.provider_used.includes('openai_compatible')
                  ? `${agentMeta.model_name || 'OpenAI-Compatible'} (${agentMeta.tools_called.length} Tools)`
                  : agentMeta.provider_used.includes('groq')
                  ? `Groq LPU (${agentMeta.tools_called.length} Tools)`
                  : agentMeta.provider_used === 'db-analytics-preview'
                  ? 'Thống kê nội bộ'
                  : 'Harness Heuristic'}
              </span>
            </div>
          )}

          {onRefresh && (
            <button
              type="button"
              onClick={handleRefreshClick}
              disabled={isLoading || isRefreshing || cooldownSeconds > 0}
              className={`min-h-[36px] flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                isPreview
                  ? 'bg-purple-600/20 hover:bg-purple-600/30 text-purple-200 border-purple-500/30'
                  : 'bg-obsidian-bg/80 hover:bg-obsidian-bg text-slate-200 hover:text-white border-slate-800 hover:border-slate-700'
              }`}
              title={cooldownSeconds > 0 ? `Vui lòng chờ ${cooldownSeconds}s` : 'Kích hoạt Thám tử AI điều tra'}
            >
              <RotateCw className={`w-3.5 h-3.5 ${isLoading || isRefreshing ? 'animate-spin text-spotify-green' : ''}`} />
              <span>
                {cooldownSeconds > 0
                  ? `Chờ ${cooldownSeconds}s`
                  : isLoading || isRefreshing
                  ? 'Đang điều tra...'
                  : isPreview
                  ? 'Kích hoạt Thám tử AI'
                  : 'Điều tra lại'}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="mt-5 z-10 relative">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4" aria-busy="true">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="bg-obsidian-bg/50 border border-slate-800/80 rounded-2xl p-4 animate-pulse space-y-3"
              >
                <div className="h-5 w-24 bg-slate-800 rounded-md" />
                <div className="h-4 w-3/4 bg-slate-800 rounded-md" />
                <div className="h-12 w-full bg-slate-800/60 rounded-md" />
                <div className="h-3 w-1/2 bg-slate-800/40 rounded-md" />
              </div>
            ))}
          </div>
        ) : error ? (
          <SectionErrorState message={error} onRetry={onRetry || onRefresh} />
        ) : safeFacts.length === 0 ? (
          <SectionEmptyState
            title="Chưa đủ dữ liệu để Agent truy vết thói quen đặc biệt"
            description="Hãy nghe thêm một số bản nhạc trong kỳ này để Agent phát hiện các sự thật âm nhạc nổi bật của bạn."
            icon={<Search className="w-5 h-5" />}
          />
        ) : (
          <div className={`grid grid-cols-1 ${safeFacts.length === 2 ? 'sm:grid-cols-2' : 'md:grid-cols-3'} gap-4`}>
            {safeFacts.map((fact) => {
              const theme = getCategoryTheme(fact.category);
              return (
                <div
                  key={fact.id}
                  className={`bg-obsidian-bg/60 border ${theme.borderColor} ${theme.glowBg} rounded-2xl p-4 flex flex-col justify-between transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5 group relative overflow-hidden`}
                >
                  <div className="space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border ${theme.badgeBg}`}>
                        {theme.icon}
                        <span>{fact.badge}</span>
                      </div>

                      {fact.metric_highlight && (
                        <span className="text-[11px] font-mono font-bold text-white bg-slate-900/80 px-2 py-0.5 rounded-md border border-slate-800">
                          {fact.metric_highlight}
                        </span>
                      )}
                    </div>

                    <h4 className="text-sm sm:text-base font-black text-white tracking-tight leading-snug group-hover:text-emerald-300 transition-colors">
                      {fact.title}
                    </h4>

                    <p className="text-xs text-slate-200 leading-relaxed">
                      {fact.description}
                    </p>
                  </div>

                  {fact.evidence && (
                    <div className="mt-3.5 pt-2.5 border-t border-slate-800/70 flex items-center justify-between text-[11px] text-text-muted">
                      <span className="text-text-muted truncate" title={fact.evidence}>
                        Bằng chứng: {fact.evidence}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
};
