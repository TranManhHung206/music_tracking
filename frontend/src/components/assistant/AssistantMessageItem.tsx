import React, { useState } from 'react';
import {
  AlertCircle,
  BarChart3,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  Database,
  FileText,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  User,
} from 'lucide-react';
import type {
  AssistantConversationTurn,
  AssistantMode,
  CitationItem,
} from '../../types/ai';
import { MarkdownMessage } from './MarkdownMessage';
import { copyTextToClipboard } from './markdownUtils';

export interface AssistantMessageItemProps {
  turn: AssistantConversationTurn;
  isAdmin: boolean;
  isLoading: boolean;
  selectedCitation: CitationItem | null;
  onSelectCitation: (citation: CitationItem) => void;
  onSelectClarification: (query: string, mode: AssistantMode) => void;
  onAddToast?: (type: 'success' | 'error' | 'info', message: string) => void;
}

const EVIDENCE_CATEGORY_LABELS: Record<string, string> = {
  observed: 'Thực tế',
  calculated: 'Tính toán',
  estimate: 'Ước lượng',
  ai_interpretation: 'AI diễn giải',
};

const DOMAIN_BADGE_MAP = {
  music_insights: {
    label: 'Dữ liệu Âm nhạc',
    className: 'bg-spotify-green/15 text-spotify-green border-spotify-green/35',
  },
  website_support: {
    label: 'Hỗ trợ Website',
    className: 'bg-sky-500/15 text-sky-300 border-sky-500/35',
  },
  clarification: {
    label: 'Cần làm rõ',
    className: 'bg-amber-500/15 text-amber-300 border-amber-500/35',
  },
};

/** Hien thi mot luot hoi - dap trong luong hoi thoai cua MusicTrack Assistant. */
export const AssistantMessageItem: React.FC<AssistantMessageItemProps> = ({
  turn,
  isAdmin,
  isLoading,
  selectedCitation,
  onSelectCitation,
  onSelectClarification,
  onAddToast,
}) => {
  const [copiedAnswer, setCopiedAnswer] = useState(false);

  const res = turn.response;
  const badge = DOMAIN_BADGE_MAP[res?.resolved_domain] || DOMAIN_BADGE_MAP.website_support;
  const answerText = typeof res?.answer === 'string' ? res.answer : '';
  const evidenceList = Array.isArray(res?.evidence) ? res.evidence : [];
  const topicList = Array.isArray(res?.topics) ? res.topics : [];
  const citationList = Array.isArray(res?.dev_citations) ? res.dev_citations : [];
  const clarificationOptions = Array.isArray(res?.clarification_options)
    ? res.clarification_options
    : [];
  const suggestedScopes = Array.isArray(res?.suggested_scopes)
    ? res.suggested_scopes
    : [];

  const handleCopyFullResponse = async () => {
    const ok = await copyTextToClipboard(answerText);
    if (ok) {
      setCopiedAnswer(true);
      window.setTimeout(() => setCopiedAnswer(false), 1800);
    } else if (onAddToast) {
      onAddToast('error', 'Không thể sao chép nội dung vào khay nhớ tạm.');
    }
  };

  return (
    <article className="space-y-3.5 animate-fade-in min-w-0">
      {/* Tin nhan nguoi dung */}
      <div className="flex justify-end">
        <div className="max-w-[92%] sm:max-w-[80%] space-y-1 min-w-0">
          <div className="flex items-center justify-end gap-1.5 text-[11px] text-text-muted px-1">
            <span>Bạn</span>
            <span aria-hidden="true">·</span>
            <time>{turn.createdAt}</time>
            <span className="w-4 h-4 rounded-full bg-spotify-green/15 border border-spotify-green/35 inline-flex items-center justify-center text-spotify-green">
              <User className="w-2.5 h-2.5" />
            </span>
          </div>
          <div className="rounded-2xl rounded-tr-sm px-4 py-2.5 bg-spotify-green/14 border border-spotify-green/35 text-sm sm:text-[15px] text-white leading-relaxed break-words">
            <p className="m-0 whitespace-pre-wrap">{turn.query}</p>
          </div>
        </div>
      </div>

      {/* Phan hoi tro ly AI */}
      <div className="rounded-2xl rounded-tl-sm bg-[#0E1526] border border-slate-800/95 overflow-hidden min-w-0">
        {/* Thanh tieu de metadata & thao tac */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 px-4 py-3 sm:px-5 bg-[#121B30]/90 border-b border-slate-800/85">
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <span className="w-6 h-6 rounded-lg bg-accent-ai/15 border border-accent-ai/35 text-purple-300 inline-flex items-center justify-center shrink-0">
              <Sparkles className="w-3.5 h-3.5" />
            </span>
            <span className="text-xs font-semibold text-white">MusicTrack Assistant</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${badge.className}`}
            >
              {badge.label}
            </span>
            {res?.scope?.label && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-800/90 text-slate-300 border border-slate-700/70 max-w-full truncate">
                Phạm vi: {res.scope.label}
              </span>
            )}
            {res?.meta?.is_fallback && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60">
                Tổng hợp dự phòng tại máy chủ
              </span>
            )}
            {res?.meta?.has_compressed_memory && (
              <span
                className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-purple-950/50 text-purple-300 border border-purple-800/50"
                title="Các lượt hội thoại cũ hơn 6 lượt đã được tự động nén thành bộ nhớ phiên"
              >
                Đã nén bộ nhớ phiên
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <time className="text-[11px] text-text-muted">{turn.createdAt}</time>
            {answerText.trim().length > 0 && (
              <button
                type="button"
                onClick={handleCopyFullResponse}
                aria-label="Sao chép toàn bộ phản hồi"
                className="min-h-[30px] inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                {copiedAnswer ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-spotify-green" />
                    <span className="text-spotify-green">Đã sao chép</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-400" />
                    <span>Sao chép</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Phan than noi dung */}
        <div className="p-4 sm:p-5 space-y-4 min-w-0">
          {res?.scope?.note && (
            <p className="text-xs text-text-muted leading-relaxed">{res.scope.note}</p>
          )}

          {/* Thong so ky thuat danh cho Quan tri vien */}
          {isAdmin && res?.dev_metrics && (
            <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-text-muted">
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span className="tabular-nums">{res.dev_metrics.latency_ms} ms</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-spotify-green" />
                  <span className="tabular-nums">
                    {res.dev_metrics.retrieved_chunks_count} chunks
                  </span>
                </span>
                {res.dev_verification && (
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="tabular-nums">
                      Trích dẫn: {Math.round((res.dev_verification.citation_existence_rate || 0) * 100)}%
                    </span>
                  </span>
                )}
              </div>
              {res.dev_verification?.all_valid ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-medium">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Nguồn đã kiểm chứng</span>
                </span>
              ) : res.dev_verification?.is_escape_hatch ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-300 font-medium">
                  <AlertCircle className="w-3 h-3" />
                  <span>Kích hoạt Escape Hatch</span>
                </span>
              ) : null}
            </div>
          )}

          {/* Noi dung Markdown */}
          <MarkdownMessage
            content={answerText}
            citations={citationList}
            onSelectCitation={onSelectCitation}
            isAdmin={isAdmin}
          />

          {/* Tuy chon lam ro y dinh */}
          {res?.needs_clarification && clarificationOptions.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {clarificationOptions.map((opt) => (
                <button
                  key={opt.mode}
                  type="button"
                  onClick={() => onSelectClarification(opt.query, opt.mode)}
                  disabled={isLoading}
                  className="min-h-[38px] inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-spotify-green/15 hover:bg-spotify-green/25 text-spotify-green border border-spotify-green/35 transition-colors cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                >
                  <HelpCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Nut chuyen nhanh pham vi thoi gian (Hybrid Smart Default) */}
          {!res?.needs_clarification && suggestedScopes.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <p className="text-[11px] text-text-muted">Chuyển nhanh phạm vi thời gian:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedScopes.map((opt, idx) => (
                  <button
                    key={`${opt.label}-${idx}`}
                    type="button"
                    onClick={() => onSelectClarification(opt.query, opt.mode)}
                    disabled={isLoading}
                    className="min-h-[34px] inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800/75 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-700/70 hover:border-spotify-green/45 transition-colors cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                  >
                    <Calendar className="w-3.5 h-3.5 text-spotify-green shrink-0" />
                    <span>{opt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Luoi can cu so lieu co cau truc (Evidence) */}
          {evidenceList.length > 0 && (
            <div className="space-y-2.5 pt-3.5 border-t border-slate-800/80">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-spotify-green shrink-0" />
                <span>Căn cứ số liệu & nguồn gốc ({evidenceList.length})</span>
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {evidenceList.map((ev, idx) => (
                  <div
                    key={`${turn.id}-ev-${idx}`}
                    className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/90 space-y-1 min-w-0"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-text-muted truncate">{ev.label}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${
                          ev.is_estimate || ev.category === 'estimate'
                            ? 'bg-amber-950/50 text-amber-300 border-amber-800/50'
                            : ev.category === 'ai_interpretation'
                            ? 'bg-purple-950/50 text-purple-300 border-purple-800/50'
                            : 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                        }`}
                      >
                        {EVIDENCE_CATEGORY_LABELS[ev.category] || 'Thực tế'}
                      </span>
                    </div>
                    <p className="text-xs font-bold text-white break-words tabular-nums">
                      {ev.value}
                    </p>
                    {ev.detail && (
                      <p className="text-[11px] text-text-muted break-words">{ev.detail}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nguon tham chieu than thien (Topics) */}
          {topicList.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/60">
              <span className="text-[11px] text-text-muted">Nguồn tham chiếu:</span>
              {topicList.map((topic) => (
                <span
                  key={`${turn.id}-${topic.id}`}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/75 border border-slate-700/60 text-[11px] text-slate-200 max-w-full"
                >
                  <FileText className="w-3 h-3 text-spotify-green shrink-0" />
                  <span className="truncate">{topic.title}</span>
                </span>
              ))}
            </div>
          )}

          {/* Ma nguon trich dan danh rieng cho Quan tri vien */}
          {isAdmin && citationList.length > 0 && (
            <div className="space-y-3 pt-3 border-t border-slate-800/80">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-spotify-green shrink-0" />
                <span>Mã nguồn trích dẫn dành cho Quản trị viên ({citationList.length})</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {citationList.map((c) => (
                  <button
                    key={c.citation_id}
                    type="button"
                    onClick={() => onSelectCitation(c)}
                    className={`text-left p-3.5 rounded-2xl border transition-colors cursor-pointer flex flex-col justify-between space-y-2 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                      selectedCitation?.citation_id === c.citation_id
                        ? 'bg-[#1E293B] border-spotify-green'
                        : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="space-y-1 min-w-0 w-full">
                      <div className="flex items-center justify-between gap-2">
                        <span className="px-2 py-0.5 rounded-md bg-spotify-green/10 text-spotify-green font-mono text-xs font-bold border border-spotify-green/20">
                          [{c.citation_id}]
                        </span>
                        <span className="text-[11px] text-text-muted font-mono tabular-nums">
                          L{c.line_start} - L{c.line_end}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-white truncate pt-1">{c.file_path}</p>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-text-muted border-t border-slate-800/80 pt-2 w-full gap-2">
                      <span className="truncate font-mono min-w-0">
                        {(c.snippet || '').slice(0, 40)}...
                      </span>
                      <span className="inline-flex items-center gap-1 text-spotify-green font-medium shrink-0">
                        <span>Xem code</span>
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
};
