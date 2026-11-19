import React, { useState } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AlertTriangle,
  Check,
  Copy,
  ExternalLink,
  Info,
  Terminal,
} from 'lucide-react';
import type { CitationItem } from '../../types/ai';
import {
  copyTextToClipboard,
  detectBlockquoteTone,
  isNumericCellText,
  normalizeMarkdownInput,
  sanitizeMarkdownUrl,
  splitCitationTokens,
  type BlockquoteTone,
} from './markdownUtils';
import { normalizeCodeLanguage, tokenizeCode, type SyntaxTokenKind } from './codeHighlight';

export interface MarkdownMessageProps {
  content: string;
  citations?: CitationItem[];
  onSelectCitation?: (citation: CitationItem) => void;
  isAdmin?: boolean;
  className?: string;
}

const REMARK_PLUGINS = [remarkGfm];

const SYNTAX_TOKEN_CLASSES: Record<SyntaxTokenKind, string> = {
  plain: 'text-slate-200',
  comment: 'text-slate-500 italic',
  string: 'text-emerald-300',
  keyword: 'text-purple-300 font-medium',
  number: 'text-cyan-300',
};

const BLOCKQUOTE_STYLES: Record<
  BlockquoteTone,
  { container: string; badge: string; iconTone: string }
> = {
  warning: {
    container: 'border-amber-700/50 border-l-amber-400 bg-amber-950/25 text-amber-100/95',
    badge: 'text-amber-300',
    iconTone: 'text-amber-400',
  },
  important: {
    container: 'border-purple-700/50 border-l-accent-ai bg-purple-950/25 text-slate-100',
    badge: 'text-purple-300',
    iconTone: 'text-accent-ai',
  },
  note: {
    container: 'border-sky-800/45 border-l-accent-cyan bg-sky-950/20 text-slate-200',
    badge: 'text-sky-300',
    iconTone: 'text-accent-cyan',
  },
  default: {
    container: 'border-slate-700/70 border-l-slate-400 bg-slate-900/60 text-slate-200',
    badge: 'text-slate-300',
    iconTone: 'text-slate-400',
  },
};

function extractPlainText(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(extractPlainText).join('');
  }
  if (React.isValidElement<{ children?: React.ReactNode }>(node)) {
    return extractPlainText(node.props.children);
  }
  return '';
}

function getAlignmentClass(
  align?: string,
  style?: React.CSSProperties
): string {
  const resolved = style?.textAlign || align;
  if (resolved === 'right') return 'text-right';
  if (resolved === 'center') return 'text-center';
  return 'text-left';
}

function renderCitationButtons(
  node: React.ReactNode,
  citations: CitationItem[],
  onSelectCitation?: (citation: CitationItem) => void,
  isAdmin: boolean = false
): React.ReactNode {
  if (typeof node === 'string') {
    if (!node.includes('[S')) return node;
    const segments = splitCitationTokens(node);
    return segments.map((seg, idx) => {
      if (seg.type === 'text') {
        return <React.Fragment key={idx}>{seg.value}</React.Fragment>;
      }
      if (!isAdmin) return null;
      const targetCitation = citations.find((c) => c.citation_id === seg.citationId);
      return (
        <button
          key={idx}
          type="button"
          onClick={() => targetCitation && onSelectCitation?.(targetCitation)}
          className={`inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded font-mono text-[11px] font-bold transition-all align-baseline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
            targetCitation
              ? 'bg-spotify-green/20 hover:bg-spotify-green/30 text-spotify-green border border-spotify-green/35 cursor-pointer'
              : 'bg-slate-800 text-slate-400 border border-slate-700/70 cursor-default'
          }`}
          title={
            targetCitation
              ? `Xem mã nguồn [${seg.citationId}]: ${targetCitation.file_path}`
              : seg.citationId
          }
        >
          {seg.raw}
        </button>
      );
    });
  }

  if (Array.isArray(node)) {
    return node.map((child, idx) => (
      <React.Fragment key={idx}>
        {renderCitationButtons(child, citations, onSelectCitation, isAdmin)}
      </React.Fragment>
    ));
  }

  return node;
}

interface MarkdownCodeBlockProps {
  code: string;
  language?: string;
}

/** Khoi ma nguon co nhan ngon ngu, to sang cu phap nhe, cuon ngang va nut sao chep. */
const MarkdownCodeBlock: React.FC<MarkdownCodeBlockProps> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  const displayLang = normalizeCodeLanguage(language) || 'code';
  const trimmedTrailing = code.replace(/\n$/, '');
  const tokens = tokenizeCode(trimmedTrailing, displayLang);

  const handleCopy = async () => {
    const ok = await copyTextToClipboard(trimmedTrailing);
    if (!ok) return;
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="my-3.5 w-full max-w-full rounded-xl border border-slate-800 bg-[#070B12] overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-3.5 py-2 bg-[#10182A] border-b border-slate-800/90">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium uppercase tracking-wider text-slate-400">
          <Terminal className="w-3.5 h-3.5 text-accent-ai shrink-0" />
          <span>{displayLang}</span>
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={`Sao chép đoạn mã ${displayLang}`}
          className="min-h-[28px] inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700/70 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-spotify-green" />
              <span className="text-spotify-green">Đã sao chép</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-slate-400" />
              <span>Sao chép mã</span>
            </>
          )}
        </button>
      </div>
      <div className="w-full max-w-full overflow-x-auto scrollbar-thin">
        <pre className="p-3.5 sm:p-4 m-0 font-mono text-xs sm:text-[13px] leading-relaxed whitespace-pre text-slate-200">
          <code>
            {tokens.map((tok, idx) =>
              tok.kind === 'plain' ? (
                <React.Fragment key={idx}>{tok.value}</React.Fragment>
              ) : (
                <span key={idx} className={SYNTAX_TOKEN_CLASSES[tok.kind]}>
                  {tok.value}
                </span>
              )
            )}
          </code>
        </pre>
      </div>
    </div>
  );
};

/** Bo hien thi noi dung Markdown GFM an toan, tai su dung cho MusicTrack Assistant. */
export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({
  content,
  citations = [],
  onSelectCitation,
  isAdmin = false,
  className = '',
}) => {
  const normalizedContent = normalizeMarkdownInput(content);

  if (!normalizedContent) {
    return (
      <p className={`text-sm text-text-muted italic ${className}`}>
        Không có nội dung phản hồi.
      </p>
    );
  }

  const withCitations = (children: React.ReactNode) =>
    renderCitationButtons(children, citations, onSelectCitation, isAdmin);

  const components: Components = {
    h1: ({ children }) => (
      <h1 className="text-base sm:text-lg font-bold text-white mt-4 mb-2.5 pb-1.5 border-b border-slate-800/80 first:mt-0 tracking-tight break-words">
        {withCitations(children)}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-[15px] sm:text-base font-bold text-white mt-4 mb-2 first:mt-0 tracking-tight break-words">
        {withCitations(children)}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-sm sm:text-[15px] font-semibold text-slate-100 mt-3.5 mb-1.5 first:mt-0 break-words">
        {withCitations(children)}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-sm font-semibold text-slate-200 mt-3 mb-1 first:mt-0 break-words">
        {withCitations(children)}
      </h4>
    ),
    p: ({ children }) => (
      <p className="my-2.5 first:mt-0 last:mb-0 text-sm sm:text-[15px] text-slate-200 leading-relaxed break-words">
        {withCitations(children)}
      </p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-white">{withCitations(children)}</strong>
    ),
    em: ({ children }) => (
      <em className="italic text-slate-100">{withCitations(children)}</em>
    ),
    del: ({ children }) => (
      <del className="line-through text-slate-400">{withCitations(children)}</del>
    ),
    ul: ({ children, className: listClassName }) => {
      const isTaskList = typeof listClassName === 'string' && listClassName.includes('contains-task-list');
      return (
        <ul
          className={`my-2.5 space-y-1.5 text-sm sm:text-[15px] text-slate-200 ${
            isTaskList ? 'pl-1 list-none' : 'pl-5 list-disc marker:text-spotify-green'
          }`}
        >
          {children}
        </ul>
      );
    },
    ol: ({ children }) => (
      <ol className="my-2.5 pl-5 space-y-1.5 list-decimal marker:text-slate-400 marker:font-semibold text-sm sm:text-[15px] text-slate-200">
        {children}
      </ol>
    ),
    li: ({ children, className: itemClassName }) => {
      const isTaskItem = typeof itemClassName === 'string' && itemClassName.includes('task-list-item');
      return (
        <li
          className={`leading-relaxed break-words [&>ul]:mt-1.5 [&>ol]:mt-1.5 [&>p]:my-1 ${
            isTaskItem ? 'flex items-start gap-2 list-none' : ''
          }`}
        >
          {withCitations(children)}
        </li>
      );
    },
    input: ({ type, checked }) => {
      if (type !== 'checkbox') return null;
      return (
        <input
          type="checkbox"
          checked={Boolean(checked)}
          readOnly
          disabled
          aria-label={checked ? 'Mục đã hoàn thành' : 'Mục chưa hoàn thành'}
          className="mt-1 h-3.5 w-3.5 rounded border-slate-600 bg-obsidian-bg accent-spotify-green shrink-0 cursor-default"
        />
      );
    },
    blockquote: ({ children }) => {
      const plain = extractPlainText(children);
      const { tone, label } = detectBlockquoteTone(plain);
      const style = BLOCKQUOTE_STYLES[tone];
      return (
        <blockquote
          className={`my-3 rounded-xl border border-l-[3px] px-3.5 py-2.5 space-y-1.5 ${style.container}`}
        >
          <div className="flex items-center gap-1.5">
            {tone === 'warning' ? (
              <AlertTriangle className={`w-3.5 h-3.5 shrink-0 ${style.iconTone}`} />
            ) : (
              <Info className={`w-3.5 h-3.5 shrink-0 ${style.iconTone}`} />
            )}
            <span className={`text-[11px] font-semibold uppercase tracking-wider ${style.badge}`}>
              {label}
            </span>
          </div>
          <div className="text-xs sm:text-sm leading-relaxed [&>p]:my-1 [&>p]:text-inherit">
            {children}
          </div>
        </blockquote>
      );
    },
    hr: () => <hr className="my-4 border-0 border-t border-slate-800/90" />,
    a: ({ href, children }) => {
      const safeHref = sanitizeMarkdownUrl(href);
      if (!safeHref) {
        return (
          <span className="text-slate-300 underline decoration-slate-600 decoration-dotted break-words [overflow-wrap:anywhere]">
            {children}
          </span>
        );
      }
      const isExternal = safeHref.startsWith('http://') || safeHref.startsWith('https://');
      return (
        <a
          href={safeHref}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
          className="inline-flex items-baseline gap-1 text-spotify-green hover:text-spotify-hover underline decoration-spotify-green/45 underline-offset-2 transition-colors break-words [overflow-wrap:anywhere] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green rounded-sm"
        >
          <span>{children}</span>
          {isExternal && <ExternalLink className="w-3 h-3 shrink-0 self-center opacity-80" />}
        </a>
      );
    },
    pre: ({ children }) => {
      const childArray = React.Children.toArray(children);
      const firstChild = childArray[0];

      if (React.isValidElement<{ className?: string; children?: React.ReactNode }>(firstChild)) {
        const cls = firstChild.props.className || '';
        const langMatch = cls.match(/language-([a-zA-Z0-9_-]+)/);
        const language = langMatch ? langMatch[1] : '';
        const rawCode = extractPlainText(firstChild.props.children);
        return <MarkdownCodeBlock code={rawCode} language={language} />;
      }

      return <MarkdownCodeBlock code={extractPlainText(children)} language="" />;
    },
    code: ({ children }) => (
      <code className="px-1.5 py-0.5 mx-0.5 rounded-md bg-[#162036] text-emerald-300 font-mono text-[0.84em] border border-slate-700/70 break-words [overflow-wrap:anywhere]">
        {children}
      </code>
    ),
    table: ({ children }) => (
      <div className="my-3.5 w-full max-w-full overflow-x-auto scrollbar-thin rounded-xl border border-slate-800 bg-[#0D1424]">
        <table className="w-full border-collapse text-xs sm:text-sm">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-[#151F35] border-b border-slate-700/80">{children}</thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-slate-800/75">{children}</tbody>
    ),
    tr: ({ children }) => (
      <tr className="even:bg-slate-900/35 hover:bg-slate-800/30 transition-colors">
        {children}
      </tr>
    ),
    th: ({ children, style, align }) => (
      <th
        style={style}
        className={`px-3 py-2.5 sm:px-3.5 text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-slate-300 whitespace-nowrap ${getAlignmentClass(
          align,
          style
        )}`}
      >
        {withCitations(children)}
      </th>
    ),
    td: ({ children, style, align }) => {
      const plain = extractPlainText(children);
      const isNumeric = isNumericCellText(plain);
      return (
        <td
          style={style}
          className={`px-3 py-2.5 sm:px-3.5 text-xs sm:text-sm align-top ${getAlignmentClass(
            align,
            style
          )} ${
            isNumeric
              ? 'tabular-nums font-medium text-white whitespace-nowrap'
              : 'text-slate-200 break-words min-w-[96px]'
          }`}
        >
          {withCitations(children)}
        </td>
      );
    },
  };

  return (
    <div className={`min-w-0 max-w-full text-slate-200 font-sans ${className}`}>
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        urlTransform={(url) => sanitizeMarkdownUrl(url) ?? ''}
        components={components}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
};
