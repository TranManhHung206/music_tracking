import React, { useState, useRef } from 'react';
import {
  Search,
  Sparkles,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  RefreshCw,
  ChevronRight,
  Database,
  ShieldCheck,
  Trash2,
  BarChart3,
  HelpCircle,
  Compass,
} from 'lucide-react';
import { api } from '../../services/api';
import { buildDemoAssistantReply } from '../../services/demoData';
import type { CalendarPeriodItem, CalendarPeriodType } from '../../types/analytics';
import type {
  AssistantConversationTurn,
  AssistantMode,
  AssistantRagMode,
  CitationItem,
} from '../../types/ai';
import { Card } from '../ui/Card';
import { SegmentedControl, type SegmentedOption } from '../ui/SegmentedControl';
import { SectionErrorState } from '../ui/SectionState';

interface CodebaseAssistantSectionProps {
  onAddToast?: (type: 'success' | 'error' | 'info', message: string) => void;
  isAdmin?: boolean;
  selectedPeriod?: CalendarPeriodItem | null;
  periodType?: CalendarPeriodType;
  isDemoMode?: boolean;
}

const ASSISTANT_MODE_OPTIONS: SegmentedOption<AssistantMode>[] = [
  { id: 'auto', label: 'Tự động' },
  { id: 'music_insights', label: 'Dữ liệu Âm nhạc' },
  { id: 'website_support', label: 'Hỗ trợ Website' },
];

const RAG_MODE_OPTIONS: SegmentedOption<AssistantRagMode>[] = [
  { id: 'full_cascade', label: 'Full Cascade' },
  { id: 'hybrid_rrf', label: 'Hybrid RRF' },
  { id: 'baseline_dense', label: 'Baseline Dense' },
];

const SAMPLE_QUERIES_BY_MODE: Record<AssistantMode, string[]> = {
  auto: [
    'Trong kỳ này tôi nghe bài hát và nghệ sĩ nào nhiều nhất?',
    'Phân tích chỉ số Audio Features và khung giờ nghe nổi bật của tôi',
    'Làm thế nào để hệ thống không ghi nhận trùng bài hát khi tôi nghe lại nhiều lần?',
    'Thông tin tài khoản Spotify và quyền riêng tư của tôi được bảo vệ như thế nào?',
  ],
  music_insights: [
    'Tổng kết lượt phát, thời lượng nghe và so sánh với kỳ trước của tôi',
    'Top bài hát, nghệ sĩ, album và thể loại nổi bật của tôi là gì?',
    'Gợi ý cho tôi vài bài hát tương đồng với bài tôi nghe nhiều nhất',
    'Khung giờ nghe cao điểm và xu hướng nghe đêm của tôi ra sao?',
  ],
  website_support: [
    'Làm thế nào để hệ thống không ghi nhận trùng bài hát khi tôi nghe lại nhiều lần?',
    'Tính năng gợi ý bài hát dựa vào những yếu tố âm nhạc nào để tìm bài tương tự?',
    'Thông tin tài khoản Spotify và quyền riêng tư của tôi được bảo vệ như thế nào?',
    'Trợ lý AI phân tích thói quen nghe nhạc (AI Persona) hoạt động như thế nào?',
  ],
};

const EVIDENCE_CATEGORY_LABELS: Record<string, string> = {
  observed: 'Thực tế',
  calculated: 'Tính toán',
  estimate: 'Ước lượng',
  ai_interpretation: 'AI diễn giải',
};

const DOMAIN_BADGE_MAP = {
  music_insights: {
    label: 'Dữ liệu Âm nhạc',
    className: 'bg-spotify-green/15 text-spotify-green border-spotify-green/30',
  },
  website_support: {
    label: 'Hỗ trợ Website',
    className: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
  },
  clarification: {
    label: 'Cần làm rõ',
    className: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  },
};

const renderFormattedText = (
  text: string,
  citations: CitationItem[],
  onSelectCitation: (c: CitationItem) => void,
  isAdmin: boolean
) => {
  const paragraphs = text.split(/\n\s*\n/);

  return (
    <div className="space-y-3">
      {paragraphs.map((para, pIdx) => {
        const lines = para.split('\n');
        return (
          <p key={pIdx} className="text-sm sm:text-[15px] text-slate-200 leading-relaxed font-sans break-words">
            {lines.map((line, lIdx) => {
              const trimmed = line.trim();
              const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ');
              const lineContent = isBullet ? trimmed.slice(2) : line;

              const tokenRegex = /(\[S\d+\]|\*\*.*?\*\*|`.*?`)/g;
              const parts = lineContent.split(tokenRegex);

              return (
                <React.Fragment key={lIdx}>
                  {lIdx > 0 && <br />}
                  {isBullet && (
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-spotify-green mr-2 align-middle" />
                  )}
                  {parts.map((part, partIdx) => {
                    if (/^\[S\d+\]$/.test(part)) {
                      if (!isAdmin) return null;
                      const label = part.slice(1, -1);
                      const targetCitation = citations.find((c) => c.citation_id === label);
                      return (
                        <button
                          key={partIdx}
                          type="button"
                          onClick={() => targetCitation && onSelectCitation(targetCitation)}
                          className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded font-mono text-xs font-bold transition-all align-baseline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                            targetCitation
                              ? 'bg-spotify-green/20 hover:bg-spotify-green/30 text-spotify-green border border-spotify-green/30 cursor-pointer shadow-sm'
                              : 'bg-slate-800 text-slate-400 cursor-default'
                          }`}
                          title={targetCitation ? `Xem mã nguồn [${label}]: ${targetCitation.file_path}` : label}
                        >
                          {part}
                        </button>
                      );
                    }
                    if (/^\*\*.*?\*\*$/.test(part)) {
                      return (
                        <strong key={partIdx} className="font-semibold text-white">
                          {part.slice(2, -2)}
                        </strong>
                      );
                    }
                    if (/^`.*?`$/.test(part)) {
                      return (
                        <code
                          key={partIdx}
                          className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-800/90 text-spotify-green font-mono text-xs border border-slate-700/60"
                        >
                          {part.slice(1, -1)}
                        </code>
                      );
                    }
                    return <span key={partIdx}>{part}</span>;
                  })}
                </React.Fragment>
              );
            })}
          </p>
        );
      })}
    </div>
  );
};

export const CodebaseAssistantSection: React.FC<CodebaseAssistantSectionProps> = ({
  onAddToast,
  isAdmin = false,
  selectedPeriod = null,
  periodType = 'week',
  isDemoMode = false,
}) => {
  const [query, setQuery] = useState('');
  const [assistantMode, setAssistantMode] = useState<AssistantMode>('auto');
  const [ragMode, setRagMode] = useState<AssistantRagMode>('full_cascade');
  const [sessionId, setSessionId] = useState<string>(() => `sess_${Date.now()}`);
  const [turns, setTurns] = useState<AssistantConversationTurn[]>([]);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastFailedRequest, setLastFailedRequest] = useState<{ q: string; mode: AssistantMode } | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);
  const threadEndRef = useRef<HTMLDivElement | null>(null);

  const handleAsk = async (targetQuery?: string, overrideMode?: AssistantMode) => {
    const q = (targetQuery !== undefined ? targetQuery : query).trim();
    const effectiveMode = overrideMode || assistantMode;
    if (!q || isLoading) return;

    if (overrideMode) {
      setAssistantMode(overrideMode);
    }
    if (targetQuery !== undefined) {
      setQuery(targetQuery);
    }

    setPendingQuery(q);
    setIsLoading(true);
    setErrorMsg(null);
    setLastFailedRequest(null);
    setSelectedCitation(null);

    try {
      if (isDemoMode) {
        const demoRes = buildDemoAssistantReply(
          q,
          effectiveMode,
          selectedPeriod,
          periodType,
          turns.length
        );
        const turn: AssistantConversationTurn = {
          id: `turn_${Date.now()}`,
          query: q,
          response: demoRes,
          createdAt: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        };
        setTurns((prev) => [...prev.slice(-11), turn]);
        setQuery('');
      } else {
        const res = await api.queryAssistant({
          query: q,
          mode: effectiveMode,
          session_id: sessionId,
          period_context: selectedPeriod
            ? {
                period_type: periodType,
                start_date: selectedPeriod.start_date,
                end_date: selectedPeriod.end_date,
                label: selectedPeriod.label,
              }
            : null,
          rag_mode: isAdmin ? ragMode : 'full_cascade',
          top_k: 5,
          use_cache: true,
        });
        const turn: AssistantConversationTurn = {
          id: `turn_${Date.now()}`,
          query: q,
          response: res,
          createdAt: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        };
        setTurns((prev) => [...prev.slice(-11), turn]);
        setQuery('');
      }
      setTimeout(() => {
        threadEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 60);
    } catch (err) {
      const msg =
        err instanceof Error && err.message
          ? err.message
          : 'Không thể kết nối đến MusicTrack Assistant. Vui lòng thử lại.';
      setErrorMsg(msg);
      setLastFailedRequest({ q, mode: effectiveMode });
      if (onAddToast) {
        onAddToast('error', msg);
      }
    } finally {
      setIsLoading(false);
      setPendingQuery(null);
    }
  };

  const handleClearSession = async () => {
    setTurns([]);
    setErrorMsg(null);
    setLastFailedRequest(null);
    setSelectedCitation(null);

    if (!isDemoMode) {
      try {
        await api.clearAssistantSession(sessionId);
      } catch {
        // Dam bao xoa sach UI ngay ca khi server cache da het han
      }
      setSessionId(`sess_${Date.now()}`);
    }
    if (onAddToast) {
      onAddToast('info', 'Đã xóa lịch sử hội thoại trong phiên hiện tại.');
    }
  };

  const handleReindex = async () => {
    setIsIndexing(true);
    try {
      const stats = await api.reindexCodebase();
      if (onAddToast) {
        onAddToast('success', `Đã nạp lại ${stats.chunks_count} chunks trong ${stats.duration_s}s.`);
      }
    } catch {
      if (onAddToast) {
        onAddToast('error', 'Lỗi khi lập chỉ mục lại codebase.');
      }
    } finally {
      setIsIndexing(false);
    }
  };

  const suggestionList = SAMPLE_QUERIES_BY_MODE[assistantMode];

  return (
    <Card variant="default" padding="md" className="rounded-3xl sm:p-8 space-y-6 relative overflow-hidden scroll-mt-24">
      <div className="absolute top-0 right-0 w-96 h-96 bg-spotify-green/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="p-2 rounded-xl bg-spotify-green/10 text-spotify-green border border-spotify-green/20 shrink-0">
              <Sparkles className="w-5 h-5" />
            </span>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-wide">
              MusicTrack Assistant
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800/80 text-slate-300 border border-slate-700/70">
              Kỳ mặc định: {selectedPeriod ? selectedPeriod.label : '30 ngày gần nhất'}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-text-muted">
            Trợ lý âm nhạc cá nhân của bạn — giải đáp số liệu nghe nhạc, gợi ý bài hát và hướng dẫn sử dụng MusicTrack
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {turns.length > 0 && (
            <button
              type="button"
              onClick={handleClearSession}
              disabled={isLoading}
              className="min-h-[38px] inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800/70 hover:bg-slate-800 text-slate-200 border border-slate-700/60 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Xóa hội thoại</span>
            </button>
          )}

          {isAdmin && (
            <button
              type="button"
              onClick={handleReindex}
              disabled={isIndexing}
              className="min-h-[38px] inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              title="Nạp lại mã nguồn vào Vector Store & BM25"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isIndexing ? 'animate-spin text-spotify-green' : ''}`} />
              <span>{isIndexing ? 'Đang index...' : 'Làm mới chỉ mục'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Mode Switcher & Search Box */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 min-w-0">
            <span className="text-xs font-medium text-text-muted">Chế độ trợ lý:</span>
            <SegmentedControl<AssistantMode>
              options={ASSISTANT_MODE_OPTIONS}
              value={assistantMode}
              onChange={(nextMode) => setAssistantMode(nextMode)}
              ariaLabel="Chọn chế độ MusicTrack Assistant"
              size="sm"
            />
          </div>

          {isAdmin && assistantMode !== 'music_insights' && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
              <span>RAG Pipeline:</span>
              <SegmentedControl<AssistantRagMode>
                options={RAG_MODE_OPTIONS}
                value={ragMode}
                onChange={(nextRagMode) => setRagMode(nextRagMode)}
                ariaLabel="Chọn chế độ truy xuất RAG cho quản trị viên"
                size="sm"
              />
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex items-center flex-1 min-w-0">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5 pointer-events-none shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
              aria-label="Nhập câu hỏi cho MusicTrack Assistant"
              placeholder={
                assistantMode === 'music_insights'
                  ? 'Hỏi về lượt phát, bài hát/nghệ sĩ nổi bật, Audio Features hoặc gợi ý bài tương đồng...'
                  : assistantMode === 'website_support'
                  ? 'Hỏi về cơ chế đồng bộ Spotify, bảo mật token, thuật toán gợi ý hay cách đọc biểu đồ...'
                  : 'Đặt câu hỏi về dữ liệu nghe nhạc của bạn hoặc cách sử dụng website...'
              }
              className="w-full min-h-[46px] bg-obsidian-bg border border-slate-700/80 rounded-2xl pl-11 pr-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-spotify-green focus-visible:ring-2 focus-visible:ring-spotify-green transition-all"
            />
          </div>
          <button
            type="button"
            onClick={() => handleAsk()}
            disabled={isLoading || !query.trim()}
            className="w-full sm:w-auto min-h-[46px] px-5 py-2.5 rounded-2xl bg-spotify-green hover:bg-spotify-hover text-black text-xs font-bold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-spotify-green/20 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            {isLoading ? 'Đang xử lý...' : 'Gửi câu hỏi'}
          </button>
        </div>

        {/* Mode-Sensitive Prompt Suggestions */}
        <div className="space-y-2">
          <span className="text-xs text-text-muted block">
            Gợi ý theo chế độ {ASSISTANT_MODE_OPTIONS.find((o) => o.id === assistantMode)?.label}:
          </span>
          <div className="flex flex-wrap gap-2">
            {suggestionList.map((sq, i) => (
              <button
                key={`${assistantMode}-${i}`}
                type="button"
                onClick={() => handleAsk(sq)}
                disabled={isLoading}
                className="text-left px-3 py-2 rounded-xl bg-slate-800/45 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 hover:text-white transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Empty Welcome Guidance */}
      {turns.length === 0 && !isLoading && !errorMsg && (
        <div className="p-4 sm:p-5 rounded-2xl bg-obsidian-bg/80 border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0">
            <Compass className="w-5 h-5 text-spotify-green shrink-0 mt-0.5" />
            <div className="space-y-1 min-w-0">
              <p className="text-xs sm:text-sm font-semibold text-white">
                Trò chuyện theo ngữ cảnh hai miền tri thức tách biệt
              </p>
              <p className="text-xs text-text-muted leading-relaxed">
                Bạn có thể hỏi nối tiếp trong cùng phiên (lưu tối đa 6 lượt gần nhất mỗi miền trong 30 phút và có thể xóa bất kỳ lúc nào). Số liệu cá nhân chỉ truy cập dữ liệu thuộc tài khoản của bạn.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Conversation History */}
      {turns.length > 0 && (
        <div className="space-y-5 pt-1">
          {turns.map((turn) => {
            const res = turn.response;
            const badge = DOMAIN_BADGE_MAP[res.resolved_domain] || DOMAIN_BADGE_MAP.website_support;

            return (
              <div key={turn.id} className="space-y-3">
                {/* User Message */}
                <div className="flex justify-end">
                  <div className="max-w-[92%] sm:max-w-[82%] rounded-2xl rounded-br-md px-4 py-2.5 bg-spotify-green/15 border border-spotify-green/35 text-sm text-white break-words">
                    <p>{turn.query}</p>
                  </div>
                </div>

                {/* Assistant Reply */}
                <div className="p-4 sm:p-5 rounded-2xl bg-obsidian-bg border border-slate-800 space-y-4">
                  {/* Meta Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                    <div className="flex flex-wrap items-center gap-2 min-w-0">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badge.className}`}>
                        {badge.label}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800/90 text-slate-300 border border-slate-700/70">
                        Phạm vi: {res.scope.label}
                      </span>
                      {res.meta?.is_fallback && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60">
                          Tổng hợp dự phòng tại máy chủ
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-text-muted">{turn.createdAt}</span>
                  </div>

                  {res.scope.note && (
                    <p className="text-[11px] text-text-muted">{res.scope.note}</p>
                  )}

                  {/* Admin Telemetry */}
                  {isAdmin && res.dev_metrics && (
                    <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-text-muted">
                      <div className="flex flex-wrap items-center gap-4">
                        <span className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          <span>{res.dev_metrics.latency_ms} ms</span>
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-spotify-green" />
                          <span>{res.dev_metrics.retrieved_chunks_count} chunks</span>
                        </span>
                        {res.dev_verification && (
                          <span className="flex items-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                            <span>
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

                  {/* Answer Text */}
                  <div>
                    {renderFormattedText(
                      res.answer,
                      res.dev_citations || [],
                      setSelectedCitation,
                      isAdmin
                    )}
                  </div>

                  {/* Clarification Options */}
                  {res.needs_clarification && Array.isArray(res.clarification_options) && res.clarification_options.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {res.clarification_options.map((opt) => (
                        <button
                          key={opt.mode}
                          type="button"
                          onClick={() => handleAsk(opt.query, opt.mode)}
                          disabled={isLoading}
                          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-spotify-green/15 hover:bg-spotify-green/25 text-spotify-green border border-spotify-green/35 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                        >
                          <HelpCircle className="w-3.5 h-3.5" />
                          <span>{opt.label}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Music Insights Evidence Grid */}
                  {Array.isArray(res.evidence) && res.evidence.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                        <BarChart3 className="w-3.5 h-3.5 text-spotify-green" />
                        <span>Căn cứ số liệu & nguồn gốc ({res.evidence.length})</span>
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {res.evidence.map((ev, idx) => (
                          <div
                            key={`${turn.id}-ev-${idx}`}
                            className="p-3 rounded-xl bg-slate-900/65 border border-slate-800/90 space-y-1 min-w-0"
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
                            <p className="text-xs font-bold text-white break-words">{ev.value}</p>
                            {ev.detail && (
                              <p className="text-[11px] text-text-muted break-words">{ev.detail}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Friendly Topic Chips */}
                  {Array.isArray(res.topics) && res.topics.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="text-[11px] text-text-muted">Nguồn tham chiếu:</span>
                      {res.topics.map((topic) => (
                        <span
                          key={`${turn.id}-${topic.id}`}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/70 border border-slate-700/60 text-[11px] text-slate-200"
                        >
                          <FileText className="w-3 h-3 text-spotify-green" />
                          <span>{topic.title}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Admin-Only Developer Citations */}
                  {isAdmin && Array.isArray(res.dev_citations) && res.dev_citations.length > 0 && (
                    <div className="space-y-3 pt-2 border-t border-slate-800/80">
                      <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-spotify-green" />
                        <span>Mã nguồn trích dẫn dành cho Quản trị viên ({res.dev_citations.length})</span>
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {res.dev_citations.map((c) => (
                          <button
                            key={c.citation_id}
                            type="button"
                            onClick={() => setSelectedCitation(c)}
                            className={`text-left p-3.5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between space-y-2 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                              selectedCitation?.citation_id === c.citation_id
                                ? 'bg-[#1E293B] border-spotify-green'
                                : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                            }`}
                          >
                            <div className="space-y-1 min-w-0 w-full">
                              <div className="flex items-center justify-between">
                                <span className="px-2 py-0.5 rounded-md bg-spotify-green/10 text-spotify-green font-mono text-xs font-bold border border-spotify-green/20">
                                  [{c.citation_id}]
                                </span>
                                <span className="text-[11px] text-text-muted font-mono">
                                  L{c.line_start} - L{c.line_end}
                                </span>
                              </div>
                              <p className="text-xs font-semibold text-white truncate pt-1">{c.file_path}</p>
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-text-muted border-t border-slate-800/80 pt-2 w-full gap-2">
                              <span className="truncate font-mono min-w-0">{c.snippet.slice(0, 40)}...</span>
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
            );
          })}
          <div ref={threadEndRef} />
        </div>
      )}

      {/* Pending / Loading State */}
      {isLoading && (
        <div className="space-y-3">
          {pendingQuery && (
            <div className="flex justify-end">
              <div className="max-w-[92%] sm:max-w-[82%] rounded-2xl rounded-br-md px-4 py-2.5 bg-spotify-green/15 border border-spotify-green/35 text-sm text-white break-words">
                <p>{pendingQuery}</p>
              </div>
            </div>
          )}
          <div className="p-5 rounded-2xl bg-obsidian-bg border border-slate-800/80 space-y-3 animate-pulse">
            <div className="h-4 bg-slate-800 rounded w-1/3" />
            <div className="space-y-2">
              <div className="h-3.5 bg-slate-800/60 rounded w-full" />
              <div className="h-3.5 bg-slate-800/60 rounded w-5/6" />
              <div className="h-3.5 bg-slate-800/60 rounded w-2/3" />
            </div>
          </div>
        </div>
      )}

      {/* Explicit Error State (No Silent Mock Fallback) */}
      {errorMsg && !isLoading && (
        <SectionErrorState
          title="Không thể nhận phản hồi từ MusicTrack Assistant"
          message={errorMsg}
          onRetry={
            lastFailedRequest
              ? () => handleAsk(lastFailedRequest.q, lastFailedRequest.mode)
              : undefined
          }
        />
      )}

      {/* Admin Code Snippet Preview Drawer */}
      {isAdmin && selectedCitation && (
        <div className="p-4 sm:p-6 rounded-2xl bg-obsidian-bg border border-spotify-green/40 space-y-3 animate-fade-in">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="px-2 py-0.5 rounded-md bg-spotify-green text-black font-mono text-xs font-bold shrink-0">
                  [{selectedCitation.citation_id}]
                </span>
                <span className="text-sm font-bold text-white truncate">{selectedCitation.file_path}</span>
              </div>
              <p className="text-xs text-text-muted font-mono">
                Dòng {selectedCitation.line_start} đến {selectedCitation.line_end}
                {selectedCitation.symbol ? ` | Symbol: ${selectedCitation.symbol}` : ''}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedCitation(null)}
              className="text-xs text-slate-300 hover:text-white px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 cursor-pointer shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
            >
              Đóng xem trước
            </button>
          </div>
          <pre className="p-4 rounded-xl bg-black/60 border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto max-h-72 leading-relaxed scrollbar-thin">
            <code>{selectedCitation.snippet}</code>
          </pre>
        </div>
      )}
    </Card>
  );
};
