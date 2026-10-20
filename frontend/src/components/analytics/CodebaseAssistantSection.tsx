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

interface CodebaseAssistantSectionProps {
  onAddToast?: (type: 'success' | 'error' | 'info', message: string) => void;
}

const SAMPLE_QUERIES = [
  'Làm thế nào để hệ thống không ghi nhận trùng bài hát khi tôi nghe lại nhiều lần?',
  'Tính năng gợi ý bài hát dựa vào những yếu tố âm nhạc nào để tìm bài tương tự?',
  'Thông tin tài khoản Spotify và quyền riêng tư của tôi được bảo vệ như thế nào?',
  'Trợ lý AI phân tích thói quen nghe nhạc (AI Persona) hoạt động như thế nào?',
];

const renderFormattedText = (
  text: string,
  citations: CitationItem[],
  onSelectCitation: (c: CitationItem) => void
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
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1DB954] mr-2 align-middle" />
                  )}
                  {parts.map((part, partIdx) => {
                    if (/^\[S\d+\]$/.test(part)) {
                      const label = part.slice(1, -1);
                      const targetCitation = citations.find((c) => c.citation_id === label);
                      return (
                        <button
                          key={partIdx}
                          type="button"
                          onClick={() => targetCitation && onSelectCitation(targetCitation)}
                          className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded font-mono text-xs font-bold transition-all align-baseline ${targetCitation
                              ? 'bg-[#1DB954]/20 hover:bg-[#1DB954]/30 text-[#1DB954] border border-[#1DB954]/30 cursor-pointer shadow-sm'
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
                          className="px-1.5 py-0.5 mx-0.5 rounded bg-slate-800/90 text-[#1DB954] font-mono text-xs border border-slate-700/60"
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
    <div className="bg-[#131B2E] border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-[#1DB954]/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="p-2 rounded-xl bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/20">
              <Code2 className="w-5 h-5" />
            </span>
            <h2 className="text-xl font-bold text-white tracking-wide">
              Agent hỗ trợ người dùng
            </h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Đặt 1 câu hỏi cho Agent nếu cần hỗ trợ cách hoạt động, sử dụng website này
          </p>
        </div>

        <button
          onClick={handleReindex}
          disabled={isIndexing}
          className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition-all cursor-pointer disabled:opacity-50"
          title="Nạp lại mã nguồn vào Vector Store & BM25"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isIndexing ? 'animate-spin text-[#1DB954]' : ''}`} />
          <span>{isIndexing ? 'Đang index...' : 'Làm mới chỉ mục'}</span>
        </button>
      </div>

      {/* Search Input Box */}
      <div className="space-y-3">
        <div className="relative flex items-center">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Hỏi bất kỳ điều gì về thuật toán, models, API hoặc kiến trúc hệ thống..."
            className="w-full bg-[#0B0F17] border border-slate-700/80 rounded-2xl pl-12 pr-32 py-3.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#1DB954] transition-all"
          />
          <div className="absolute right-2 flex items-center space-x-2">
            <button
              onClick={() => handleSearch()}
              disabled={isLoading || !query.trim()}
              className="px-4 py-2 rounded-xl bg-[#1DB954] hover:bg-[#1ED760] text-black text-xs font-bold transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-[#1DB954]/20"
            >
              {isLoading ? 'Đang tìm...' : 'Tra cứu'}
            </button>
          </div>
        </div>

        {/* Pipeline Mode Controls & Sample Queries */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2 text-slate-400">
            <span>Chế độ:</span>
            <div className="inline-flex rounded-lg bg-[#0B0F17] p-1 border border-slate-800">
              <button
                onClick={() => setMode('full_cascade')}
                className={`px-2.5 py-1 rounded-md transition-all font-medium ${mode === 'full_cascade' ? 'bg-[#1DB954] text-black font-bold' : 'text-slate-400 hover:text-white'
                  }`}
              >
                Full Cascade
              </button>
              <button
                onClick={() => setMode('hybrid_rrf')}
                className={`px-2.5 py-1 rounded-md transition-all font-medium ${mode === 'hybrid_rrf' ? 'bg-[#1DB954] text-black font-bold' : 'text-slate-400 hover:text-white'
                  }`}
              >
                Hybrid RRF
              </button>
              <button
                onClick={() => setMode('baseline_dense')}
                className={`px-2.5 py-1 rounded-md transition-all font-medium ${mode === 'baseline_dense' ? 'bg-[#1DB954] text-black font-bold' : 'text-slate-400 hover:text-white'
                  }`}
              >
                Baseline Dense
              </button>
            </div>
          </div>

          <span className="text-slate-500 hidden sm:inline">Gợi ý câu hỏi:</span>
        </div>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-2 pt-1">
          {SAMPLE_QUERIES.map((sq, i) => (
            <button
              key={i}
              onClick={() => handleSearch(sq)}
              className="text-left px-3 py-1.5 rounded-xl bg-slate-800/40 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 hover:text-white transition-all cursor-pointer"
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
          {/* Metadata Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-2xl bg-[#0B0F17] border border-slate-800 text-xs text-slate-400">
            <div className="flex items-center space-x-4">
              <span className="flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{response.latency_ms} ms</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-[#1DB954]" />
                <span>{response.retrieved_chunks_count} chunks</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span>
                  Trích dẫn: {Math.round((response.verification?.citation_existence_rate || 0) * 100)}%
                </span>
              </span>
            </div>

            {response.verification?.all_valid ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 font-medium">
                <CheckCircle2 className="w-3 h-3" />
                <span>Nguồn đã kiểm chứng</span>
              </span>
            ) : response.verification?.is_escape_hatch ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-amber-950/60 border border-amber-800/60 text-amber-400 font-medium">
                <AlertCircle className="w-3 h-3" />
                <span>Kích hoạt Escape Hatch</span>
              </span>
            ) : null}
          </div>

          {/* Answer Text */}
          <div className="p-6 rounded-2xl bg-[#0B0F17] border border-slate-800 space-y-4">
            <div className="flex items-center space-x-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-[#1DB954]" />
              <span>Câu trả lời từ Trợ lý Hỗ trợ</span>
            </div>
            <div>
              {renderFormattedText(response.answer, response.citations || [], setSelectedCitation)}
            </div>
          </div>

          {/* Citations Grid */}
          {Array.isArray(response.citations) && response.citations.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-2">
                <FileText className="w-3.5 h-3.5 text-[#1DB954]" />
                <span>Tài liệu & Đoạn mã nguồn trích dẫn ({response.citations.length})</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {response.citations.map((c) => (
                  <button
                    key={c.citation_id}
                    onClick={() => setSelectedCitation(c)}
                    className={`text-left p-4 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between space-y-3 ${selectedCitation?.citation_id === c.citation_id
                        ? 'bg-[#1E293B] border-[#1DB954]'
                        : 'bg-[#0B0F17] border-slate-800 hover:border-slate-700'
                      }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded-md bg-[#1DB954]/10 text-[#1DB954] font-mono text-xs font-bold border border-[#1DB954]/20">
                          [{c.citation_id}]
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          L{c.line_start} - L{c.line_end}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-white truncate pt-1">{c.file_path}</p>
                      {c.symbol && (
                        <p className="text-[11px] text-slate-400 font-mono truncate">Symbol: {c.symbol}</p>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
                      <span className="truncate max-w-[200px] text-slate-500 font-mono">
                        {c.snippet.slice(0, 40)}...
                      </span>
                      <span className="inline-flex items-center space-x-1 text-[#1DB954] hover:underline font-medium">
                        <span>Xem code</span>
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Citation Code Preview Drawer / Modal */}
          {selectedCitation && (
            <div className="p-6 rounded-2xl bg-[#0B0F17] border border-[#1DB954]/40 space-y-3 animate-in fade-in">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="space-y-0.5">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 rounded-md bg-[#1DB954] text-black font-mono text-xs font-bold">
                      [{selectedCitation.citation_id}]
                    </span>
                    <span className="text-sm font-bold text-white">{selectedCitation.file_path}</span>
                  </div>
                  <p className="text-xs text-slate-400 font-mono">
                    Dòng {selectedCitation.line_start} đến {selectedCitation.line_end}
                    {selectedCitation.symbol ? ` | Symbol: ${selectedCitation.symbol}` : ''}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedCitation(null)}
                  className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 cursor-pointer"
                >
                  Đóng xem trước
                </button>
              </div>

              <div className="relative">
                <pre className="p-4 rounded-xl bg-black/60 border border-slate-800 font-mono text-xs text-slate-200 overflow-x-auto max-h-72 leading-relaxed">
                  <code>{selectedCitation.snippet}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
