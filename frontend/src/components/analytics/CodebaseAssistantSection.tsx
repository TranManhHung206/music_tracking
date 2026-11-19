import React, { useState, useRef } from 'react';
import {
  ArrowDown,
  Check,
  Compass,
  Copy,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Trash2,
  User,
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
import { AssistantMessageItem } from '../assistant/AssistantMessageItem';
import { copyTextToClipboard } from '../assistant/markdownUtils';

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

const EMPTY_GUIDANCE_BY_MODE: Record<
  AssistantMode,
  { title: string; description: string }
> = {
  auto: {
    title: 'Trò chuyện thông minh trên hai miền tri thức tách biệt',
    description:
      'MusicTrack Assistant tự nhận diện câu hỏi về số liệu nghe nhạc cá nhân hoặc hướng dẫn sử dụng website. Phiên hội thoại lưu tối đa 6 lượt gần nhất mỗi miền trong 30 phút và có thể xóa bất kỳ lúc nào.',
  },
  music_insights: {
    title: 'Phân tích chuyên sâu dữ liệu nghe nhạc Spotify của bạn',
    description:
      'Hỏi về lượt phát, top bài hát/nghệ sĩ/album, xu hướng tăng giảm giữa các kỳ, đặc trưng Audio Features hoặc gợi ý bài hát tương đồng bằng mô hình KNN.',
  },
  website_support: {
    title: 'Giải đáp tính năng, cơ chế đồng bộ và bảo mật MusicTrack',
    description:
      'Tìm hiểu cách hoạt động của cơ chế chống trùng lặp lượt nghe, quy trình mã hóa token Spotify, cách đọc biểu đồ phân tích và cách tính các chỉ số trên Dashboard.',
  },
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
  const [pendingMode, setPendingMode] = useState<AssistantMode>('auto');
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [lastFailedRequest, setLastFailedRequest] = useState<{
    q: string;
    mode: AssistantMode;
  } | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [showScrollToLatest, setShowScrollToLatest] = useState(false);

  const threadContainerRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef(true);

  const scrollThreadToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const container = threadContainerRef.current;
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    });
    isNearBottomRef.current = true;
    setShowScrollToLatest(false);
  };

  const handleThreadScroll = () => {
    const container = threadContainerRef.current;
    if (!container) return;
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;
    const nearBottom = distanceFromBottom <= 120;
    isNearBottomRef.current = nearBottom;
    setShowScrollToLatest(!nearBottom && container.scrollHeight > container.clientHeight + 80);
  };

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
    setPendingMode(effectiveMode);
    setIsLoading(true);
    setErrorMsg(null);
    setLastFailedRequest(null);
    setSelectedCitation(null);

    // Chi tu cuon xuong phan dang tao neu nguoi dung dang dung gan cuoi hoi thoai
    if (isNearBottomRef.current) {
      window.setTimeout(() => {
        if (isNearBottomRef.current) {
          scrollThreadToBottom('smooth');
        }
      }, 40);
    }

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
          createdAt: new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
          }),
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
          createdAt: new Date().toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        };
        setTurns((prev) => [...prev.slice(-11), turn]);
        setQuery('');
      }

      window.setTimeout(() => {
        if (isNearBottomRef.current) {
          scrollThreadToBottom('smooth');
        } else {
          setShowScrollToLatest(true);
        }
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
    setShowScrollToLatest(false);
    isNearBottomRef.current = true;

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
        onAddToast(
          'success',
          `Đã nạp lại ${stats.chunks_count} chunks trong ${stats.duration_s}s.`
        );
      }
    } catch {
      if (onAddToast) {
        onAddToast('error', 'Lỗi khi lập chỉ mục lại codebase.');
      }
    } finally {
      setIsIndexing(false);
    }
  };

  const handleCopyCitationSnippet = async () => {
    if (!selectedCitation?.snippet) return;
    const ok = await copyTextToClipboard(selectedCitation.snippet);
    if (!ok) return;
    setCopiedSnippet(true);
    window.setTimeout(() => setCopiedSnippet(false), 1800);
  };

  const suggestionList = SAMPLE_QUERIES_BY_MODE[assistantMode];
  const emptyGuidance = EMPTY_GUIDANCE_BY_MODE[assistantMode];
  const hasConversation = turns.length > 0 || isLoading;

  return (
    <Card
      variant="default"
      padding="md"
      className="rounded-3xl sm:p-7 space-y-5 relative overflow-hidden scroll-mt-24"
    >
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="p-2 rounded-xl bg-accent-ai/12 text-purple-300 border border-accent-ai/30 shrink-0">
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
            Trợ lý âm nhạc cá nhân của bạn — phân tích số liệu nghe nhạc, bảng xếp hạng, gợi ý bài hát và hướng dẫn sử dụng MusicTrack
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {turns.length > 0 && (
            <button
              type="button"
              onClick={handleClearSession}
              disabled={isLoading}
              className="min-h-[38px] inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-800/70 hover:bg-slate-800 text-slate-200 border border-slate-700/60 transition-colors cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
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
              className="min-h-[38px] inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 transition-colors cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              title="Nạp lại mã nguồn vào Vector Store & BM25"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${isIndexing ? 'animate-spin text-spotify-green' : ''}`}
              />
              <span>{isIndexing ? 'Đang index...' : 'Làm mới chỉ mục'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Mode Switcher & Input Controls */}
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
              className="max-w-full flex-wrap"
            />
          </div>

          {isAdmin && assistantMode !== 'music_insights' && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted min-w-0">
              <span>RAG Pipeline:</span>
              <SegmentedControl<AssistantRagMode>
                options={RAG_MODE_OPTIONS}
                value={ragMode}
                onChange={(nextRagMode) => setRagMode(nextRagMode)}
                ariaLabel="Chọn chế độ truy xuất RAG cho quản trị viên"
                size="sm"
                className="max-w-full flex-wrap"
              />
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex items-center flex-1 min-w-0">
            <Search className="w-4 h-4 sm:w-5 sm:h-5 text-slate-400 absolute left-3.5 pointer-events-none shrink-0" />
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
              className="w-full min-h-[46px] bg-obsidian-bg border border-slate-700/80 rounded-2xl pl-10 sm:pl-11 pr-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-spotify-green focus-visible:ring-2 focus-visible:ring-spotify-green transition-colors"
            />
          </div>
          <button
            type="button"
            onClick={() => handleAsk()}
            disabled={isLoading || !query.trim()}
            className="w-full sm:w-auto min-h-[46px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-2xl bg-spotify-green hover:bg-spotify-hover text-black text-xs font-bold transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-spotify-green/20 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            <Send className="w-3.5 h-3.5 shrink-0" />
            <span>{isLoading ? 'Đang xử lý...' : 'Gửi câu hỏi'}</span>
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
                className="text-left px-3 py-2 rounded-xl bg-slate-800/45 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 hover:text-white transition-colors cursor-pointer disabled:opacity-50 break-words focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Empty Welcome Guidance */}
      {!hasConversation && !errorMsg && (
        <div className="p-4 sm:p-5 rounded-2xl bg-obsidian-bg/85 border border-slate-800/85 flex items-start gap-3.5 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-spotify-green/10 border border-spotify-green/25 flex items-center justify-center text-spotify-green shrink-0 mt-0.5">
            <Compass className="w-4 h-4" />
          </div>
          <div className="space-y-1 min-w-0">
            <p className="text-xs sm:text-sm font-semibold text-white">
              {emptyGuidance.title}
            </p>
            <p className="text-xs text-text-muted leading-relaxed">
              {emptyGuidance.description}
            </p>
          </div>
        </div>
      )}

      {/* Conversation Thread */}
      {hasConversation && (
        <div className="relative min-w-0">
          <div
            ref={threadContainerRef}
            onScroll={handleThreadScroll}
            role="log"
            aria-label="Lịch sử hội thoại MusicTrack Assistant"
            aria-live="polite"
            className="max-h-[70vh] sm:max-h-[760px] overflow-y-auto scrollbar-thin space-y-6 pr-0.5 sm:pr-1.5 pt-1"
          >
            {turns.map((turn) => (
              <AssistantMessageItem
                key={turn.id}
                turn={turn}
                isAdmin={isAdmin}
                isLoading={isLoading}
                selectedCitation={selectedCitation}
                onSelectCitation={setSelectedCitation}
                onSelectClarification={(nextQ, nextMode) => handleAsk(nextQ, nextMode)}
                onAddToast={onAddToast}
              />
            ))}

            {/* Pending / Generating State */}
            {isLoading && (
              <div className="space-y-3.5 animate-fade-in">
                {pendingQuery && (
                  <div className="flex justify-end">
                    <div className="max-w-[92%] sm:max-w-[80%] space-y-1 min-w-0">
                      <div className="flex items-center justify-end gap-1.5 text-[11px] text-text-muted px-1">
                        <span>Bạn</span>
                        <span className="w-4 h-4 rounded-full bg-spotify-green/15 border border-spotify-green/35 inline-flex items-center justify-center text-spotify-green">
                          <User className="w-2.5 h-2.5" />
                        </span>
                      </div>
                      <div className="rounded-2xl rounded-tr-sm px-4 py-2.5 bg-spotify-green/14 border border-spotify-green/35 text-sm sm:text-[15px] text-white leading-relaxed break-words">
                        <p className="m-0 whitespace-pre-wrap">{pendingQuery}</p>
                      </div>
                    </div>
                  </div>
                )}

                <div
                  role="status"
                  aria-label="Đang tạo phản hồi từ MusicTrack Assistant"
                  className="rounded-2xl rounded-tl-sm bg-[#0E1526] border border-slate-800/90 overflow-hidden"
                >
                  <div className="flex items-center gap-2.5 px-4 py-3 sm:px-5 bg-[#121B30]/90 border-b border-slate-800/80">
                    <span className="w-6 h-6 rounded-lg bg-accent-ai/15 border border-accent-ai/35 text-purple-300 inline-flex items-center justify-center shrink-0">
                      <Sparkles className="w-3.5 h-3.5 animate-pulse" />
                    </span>
                    <span className="text-xs font-semibold text-white">MusicTrack Assistant</span>
                    <span className="text-xs text-text-muted">
                      {pendingMode === 'website_support'
                        ? 'Đang tra cứu tài liệu và cơ chế hệ thống...'
                        : 'Đang tổng hợp dữ liệu nghe nhạc và tạo câu trả lời...'}
                    </span>
                  </div>
                  <div className="p-4 sm:p-5 space-y-3 animate-pulse">
                    <div className="h-4 bg-slate-800 rounded-md w-2/5" />
                    <div className="space-y-2">
                      <div className="h-3.5 bg-slate-800/70 rounded-md w-full" />
                      <div className="h-3.5 bg-slate-800/70 rounded-md w-11/12" />
                      <div className="h-3.5 bg-slate-800/60 rounded-md w-3/4" />
                    </div>
                    <div className="h-20 bg-slate-900/80 border border-slate-800/70 rounded-xl w-full" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Nut nhay xuong cuoi luong khi nguoi dung dang doc tin nhan cu */}
          {showScrollToLatest && (
            <div className="sticky bottom-2 flex justify-center pt-2 pointer-events-none">
              <button
                type="button"
                onClick={() => scrollThreadToBottom('smooth')}
                className="pointer-events-auto min-h-[34px] inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-obsidian-elevated hover:bg-slate-700 text-xs font-semibold text-white border border-slate-700 shadow-lg transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                <ArrowDown className="w-3.5 h-3.5 text-spotify-green" />
                <span>Xuống phản hồi mới nhất</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Explicit Error State */}
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
        <div className="p-4 sm:p-5 rounded-2xl bg-[#0B101D] border border-spotify-green/40 space-y-3 animate-fade-in">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
            <div className="space-y-0.5 min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <span className="px-2 py-0.5 rounded-md bg-spotify-green text-black font-mono text-xs font-bold shrink-0">
                  [{selectedCitation.citation_id}]
                </span>
                <span className="text-sm font-bold text-white truncate">
                  {selectedCitation.file_path}
                </span>
              </div>
              <p className="text-xs text-text-muted font-mono">
                Dòng {selectedCitation.line_start} đến {selectedCitation.line_end}
                {selectedCitation.symbol ? ` | Symbol: ${selectedCitation.symbol}` : ''}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleCopyCitationSnippet}
                className="min-h-[32px] inline-flex items-center gap-1.5 text-xs text-slate-200 hover:text-white px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700/70 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                {copiedSnippet ? (
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
              <button
                type="button"
                onClick={() => setSelectedCitation(null)}
                className="min-h-[32px] text-xs text-slate-300 hover:text-white px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                Đóng xem trước
              </button>
            </div>
          </div>
          <pre className="p-4 rounded-xl bg-[#070B12] border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto max-h-72 leading-relaxed scrollbar-thin">
            <code>{selectedCitation.snippet}</code>
          </pre>
        </div>
      )}
    </Card>
  );
};
