export type BlockquoteTone = 'note' | 'warning' | 'important' | 'default';

export interface BlockquoteMeta {
  tone: BlockquoteTone;
  label: string;
}

export type CitationSegment =
  | { type: 'text'; value: string }
  | { type: 'citation'; citationId: string; raw: string };

const ALLOWED_URL_PROTOCOLS = new Set(['http:', 'https:', 'mailto:']);
const CITATION_TOKEN_REGEX = /(\[S\d+\])/g;
const NUMERIC_CELL_REGEX = /^[+-]?\d[\d.,]*(\s*(%|lượt|phút|giờ|h|ms|s|bpm))?$/i;

function stripControlChars(input: string): string {
  let result = '';
  for (let i = 0; i < input.length; i += 1) {
    const code = input.charCodeAt(i);
    if (code >= 0x20 && code !== 0x7f) {
      result += input[i];
    }
  }
  return result;
}

/** Xac thuc va lam sach URL trong Markdown, chi chap nhan giao thuc an toan. */
export function sanitizeMarkdownUrl(rawUrl?: string | null): string | null {
  if (typeof rawUrl !== 'string') return null;
  const cleaned = stripControlChars(rawUrl).trim();
  if (!cleaned) return null;

  if (cleaned.startsWith('#')) {
    return cleaned;
  }
  if (cleaned.startsWith('/') && !cleaned.startsWith('//')) {
    return cleaned;
  }

  try {
    const parsed = new URL(cleaned);
    if (!ALLOWED_URL_PROTOCOLS.has(parsed.protocol.toLowerCase())) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

/** Chuan hoa chuoi Markdown dau vao va tu dong rao code block chua dong. */
export function normalizeMarkdownInput(raw?: string | null): string {
  if (typeof raw !== 'string') return '';
  const normalized = raw.replace(/\r\n?/g, '\n');
  if (!normalized.trim()) return '';

  const lines = normalized.split('\n');
  let activeFenceChar: '`' | '~' | null = null;
  let activeFenceLength = 0;

  for (const line of lines) {
    const trimmed = line.trimStart();
    if (!activeFenceChar) {
      const openMatch = trimmed.match(/^(`{3,}|~{3,})/);
      if (openMatch) {
        const marker = openMatch[1];
        const char = marker[0] as '`' | '~';
        const rest = trimmed.slice(marker.length);
        // Backtick info strings cannot contain backticks per CommonMark
        if (char === '~' || !rest.includes('`')) {
          activeFenceChar = char;
          activeFenceLength = marker.length;
        }
      }
    } else {
      const closePattern = activeFenceChar === '`' ? /^(`{3,})\s*$/ : /^(~{3,})\s*$/;
      const closeMatch = trimmed.match(closePattern);
      if (closeMatch && closeMatch[1].length >= activeFenceLength) {
        activeFenceChar = null;
        activeFenceLength = 0;
      }
    }
  }

  if (activeFenceChar) {
    return `${normalized}\n${activeFenceChar.repeat(activeFenceLength)}`;
  }

  return normalized;
}

/** Nhan dien muc do ngu nghia cua blockquote de hien thi nhan ro rang. */
export function detectBlockquoteTone(rawText: string): BlockquoteMeta {
  const text = (rawText || '').trim();
  if (/^(cảnh báo|warning|caution|nguy hiểm)\s*:/i.test(text)) {
    return { tone: 'warning', label: 'Cảnh báo' };
  }
  if (/^(quan trọng|important|chú ý)\s*:/i.test(text)) {
    return { tone: 'important', label: 'Quan trọng' };
  }
  if (/^(lưu ý|note|ghi chú|giới hạn|limitation|caveat|ước lượng)\s*:/i.test(text)) {
    return { tone: 'note', label: 'Ghi chú' };
  }
  return { tone: 'default', label: 'Ghi chú' };
}

/** Tach an toan cac ma trich dan dang [S1], [S2] trong chuoi van ban. */
export function splitCitationTokens(text: string): CitationSegment[] {
  if (!text || !text.includes('[S')) {
    return [{ type: 'text', value: text }];
  }

  const parts = text.split(CITATION_TOKEN_REGEX);
  const segments: CitationSegment[] = [];

  for (const part of parts) {
    if (!part) continue;
    if (/^\[S\d+\]$/.test(part)) {
      segments.push({
        type: 'citation',
        citationId: part.slice(1, -1),
        raw: part,
      });
    } else {
      segments.push({ type: 'text', value: part });
    }
  }

  return segments;
}

/** Kiem tra noi dung o bang co phai dang so lieu de ap dung tabular-nums. */
export function isNumericCellText(text: string): boolean {
  const trimmed = (text || '').trim();
  if (!trimmed) return false;
  return NUMERIC_CELL_REGEX.test(trimmed);
}

/** Sao chep van ban vao clipboard co nhanh du phong an toan. */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (!text) return false;
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to legacy textarea copy fallback
  }

  try {
    if (typeof document === 'undefined') return false;
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    textarea.style.pointerEvents = 'none';
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}
