import React, { useState } from 'react';
import {
  Search,
  Code2,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  RefreshCw,
  ChevronRight,
  Database,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../../services/api';
import type { CodebaseQueryResponse, CitationItem } from '../../types/ai';
import { Card } from '../ui/Card';
import { SegmentedControl, type SegmentedOption } from '../ui/SegmentedControl';

interface CodebaseAssistantSectionProps {
  onAddToast?: (type: 'success' | 'error' | 'info', message: string) => void;
  isAdmin?: boolean;
}

type RetrievalMode = 'full_cascade' | 'hybrid_rrf' | 'baseline_dense';

const MODE_OPTIONS: SegmentedOption<RetrievalMode>[] = [
  { id: 'full_cascade', label: 'Full Cascade' },
  { id: 'hybrid_rrf', label: 'Hybrid RRF' },
  { id: 'baseline_dense', label: 'Baseline Dense' },
];

const SAMPLE_QUERIES = [
  'Làm thế nào để hệ thống không ghi nhận trùng bài hát khi tôi nghe lại nhiều lần?',
  'Tính năng gợi ý bài hát dựa vào những yếu tố âm nhạc nào để tìm bài tương tự?',
  'Thông tin tài khoản Spotify và quyền riêng tư của tôi được bảo vệ như thế nào?',
  'Trợ lý AI phân tích thói quen nghe nhạc (AI Persona) hoạt động như thế nào?',
];

const renderFormattedText = (
  text: string,
  citations: CitationItem[],
  onSelectCitation: (c: CitationItem) => void,
  isAdmin: boolean
) => {
  const paragraphs = text.split(/\n\s*\n/);

  return (
    <div className="space-y-3.5">
      {paragraphs.map((para, pIdx) => {
        const lines = para.split('\n');
        return (
          <p key={pIdx} className="text-sm sm:text-base text-slate-200 leading-relaxed font-sans">
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
}) => {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'full_cascade' | 'hybrid_rrf' | 'baseline_dense'>('full_cascade');
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [response, setResponse] = useState<CodebaseQueryResponse | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  const handleSearch = async (targetQuery?: string) => {
    const q = (targetQuery !== undefined ? targetQuery : query).trim();
    if (!q) return;

    if (targetQuery !== undefined) {
      setQuery(targetQuery);
    }

    setIsLoading(true);
    setSelectedCitation(null);

    try {
      const res = await api.queryCodebase({
        query: q,
        mode: mode,
        top_k: 5,
        use_cache: true,
      });
      setResponse(res);
    } catch {
      if (onAddToast) {
        onAddToast('error', 'Không thể kết nối đến hệ thống RAG Codebase.');
      }
    } finally {
      setIsLoading(false);
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

  return (
    <Card variant="default" padding="md" className="rounded-3xl sm:p-8 space-y-6 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-spotify-green/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5 sm:pb-6">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-spotify-green/10 text-spotify-green border border-spotify-green/20 shrink-0">
              <Code2 className="w-5 h-5" />
            </span>
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-wide">
              Agent hỗ trợ người dùng
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-text-muted">
            Đặt câu hỏi cho Agent nếu cần hỗ trợ cách hoạt động và sử dụng website này
          </p>
        </div>

        {isAdmin && (
          <button
            type="button"
            onClick={handleReindex}
            disabled={isIndexing}
            className="min-h-[38px] inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/60 transition-all cursor-pointer disabled:opacity-50 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
            title="Nạp lại mã nguồn vào Vector Store & BM25"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIndexing ? 'animate-spin text-spotify-green' : ''}`} />
            <span>{isIndexing ? 'Đang index...' : 'Làm mới chỉ mục'}</span>
          </button>
        )}
      </div>

      {/* Search Input Box - Stack cleanly trên mobile nhỏ */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex items-center flex-1 min-w-0">
            <Search className="w-5 h-5 text-slate-400 absolute left-3.5 pointer-events-none shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              aria-label="Nhập câu hỏi hỗ trợ"
              placeholder="Đặt câu hỏi về tính năng, biểu đồ, bảo mật hoặc cách sử dụng..."
              className="w-full min-h-[46px] bg-obsidian-bg border border-slate-700/80 rounded-2xl pl-11 pr-4 py-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:border-spotify-green focus-visible:ring-2 focus-visible:ring-spotify-green transition-all"
            />
          </div>
          <button
            type="button"
            onClick={() => handleSearch()}
            disabled={isLoading || !query.trim()}
            className="w-full sm:w-auto min-h-[46px] px-5 py-2.5 rounded-2xl bg-spotify-green hover:bg-spotify-hover text-black text-xs font-bold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-spotify-green/20 shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
          >
            {isLoading ? 'Đang tìm...' : 'Tra cứu'}
          </button>
        </div>

        {/* Pipeline Mode Controls & Sample Queries */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          {isAdmin && (
            <div className="flex flex-wrap items-center gap-2 text-text-muted">
              <span>Chế độ:</span>
              <SegmentedControl
                options={MODE_OPTIONS}
                value={mode}
                onChange={setMode}
                ariaLabel="Chọn chế độ truy xuất RAG"
                size="sm"
              />
            </div>
          )}

          <span className="text-text-muted">Gợi ý câu hỏi:</span>
        </div>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-2 pt-1">
          {SAMPLE_QUERIES.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSearch(sq)}
              className="text-left px-3 py-2 rounded-xl bg-slate-800/45 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 hover:text-white transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="p-6 rounded-2xl bg-[#0B0F17] border border-slate-800/80 space-y-4 animate-pulse">
          <div className="h-4 bg-slate-800 rounded w-1/4" />
          <div className="space-y-2">
            <div className="h-3.5 bg-slate-800/60 rounded w-full" />
            <div className="h-3.5 bg-slate-800/60 rounded w-5/6" />
            <div className="h-3.5 bg-slate-800/60 rounded w-3/4" />
          </div>
          <div className="flex space-x-3 pt-2">
            <div className="h-8 bg-slate-800 rounded-xl w-32" />
            <div className="h-8 bg-slate-800 rounded-xl w-32" />
          </div>
        </div>
      )}

      {/* Response Box */}
      {response && !isLoading && (
        <div className="space-y-6 pt-2">
          {/* Metadata Bar (Admin/Developer only) */}
          {isAdmin && (
            <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-obsidian-bg border border-slate-800 text-xs text-text-muted">
              <div className="flex flex-wrap items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>{response.latency_ms} ms</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-spotify-green" />
                  <span>{response.retrieved_chunks_count} chunks</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  <span>
                    Trích dẫn: {Math.round((response.verification?.citation_existence_rate || 0) * 100)}%
                  </span>
                </span>
              </div>

              {response.verification?.all_valid ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 font-medium">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Nguồn đã kiểm chứng</span>
                </span>
              ) : response.verification?.is_escape_hatch ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-300 font-medium">
                  <AlertCircle className="w-3 h-3" />
                  <span>Kích hoạt Escape Hatch</span>
                </span>
              ) : null}
            </div>
          )}

          {/* Answer Text */}
          <div className="p-4 sm:p-6 rounded-2xl bg-obsidian-bg border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 text-text-muted text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-spotify-green" />
              <span>Câu trả lời từ Trợ lý Hỗ trợ</span>
            </div>
            <div>
              {renderFormattedText(response.answer, response.citations || [], setSelectedCitation, isAdmin)}
            </div>
          </div>

          {/* Citations Grid (Admin/Developer only) */}
          {isAdmin && Array.isArray(response.citations) && response.citations.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-3.5 h-3.5 text-spotify-green" />
                <span>Tài liệu & Đoạn mã nguồn trích dẫn ({response.citations.length})</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {response.citations.map((c) => (
                  <button
                    key={c.citation_id}
                    type="button"
                    onClick={() => setSelectedCitation(c)}
                    className={`text-left p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between space-y-3 min-w-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                      selectedCitation?.citation_id === c.citation_id
                        ? 'bg-[#1E293B] border-spotify-green'
                        : 'bg-obsidian-bg border-slate-800 hover:border-slate-700'
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
                      {c.symbol && (
                        <p className="text-[11px] text-text-muted font-mono truncate">Symbol: {c.symbol}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-text-muted border-t border-slate-800/80 pt-2 w-full gap-2">
                      <span className="truncate text-text-muted font-mono min-w-0">
                        {c.snippet.slice(0, 40)}...
                      </span>
                      <span className="inline-flex items-center gap-1 text-spotify-green hover:underline font-medium shrink-0">
                        <span>Xem code</span>
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Citation Code Preview Drawer / Modal (Admin/Developer only) */}
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

              <div className="relative">
                <pre className="p-4 rounded-xl bg-black/60 border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto max-h-72 leading-relaxed scrollbar-thin">
                  <code>{selectedCitation.snippet}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
