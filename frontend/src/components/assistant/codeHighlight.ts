export type SyntaxTokenKind = 'plain' | 'comment' | 'string' | 'keyword' | 'number';

export interface SyntaxToken {
  kind: SyntaxTokenKind;
  value: string;
}

const LANGUAGE_ALIASES: Record<string, string> = {
  py: 'python',
  python: 'python',
  js: 'javascript',
  jsx: 'javascript',
  javascript: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  typescript: 'typescript',
  json: 'json',
  sql: 'sql',
  sh: 'bash',
  bash: 'bash',
  shell: 'bash',
  powershell: 'bash',
  ps1: 'bash',
};

const KEYWORDS_BY_LANG: Record<string, Set<string>> = {
  python: new Set([
    'def', 'class', 'return', 'import', 'from', 'as', 'if', 'elif', 'else',
    'for', 'while', 'in', 'not', 'and', 'or', 'is', 'None', 'True', 'False',
    'try', 'except', 'finally', 'with', 'raise', 'pass', 'break', 'continue',
    'lambda', 'async', 'await', 'yield', 'self',
  ]),
  javascript: new Set([
    'function', 'const', 'let', 'var', 'return', 'import', 'export', 'from',
    'default', 'if', 'else', 'for', 'while', 'switch', 'case', 'break', 'continue',
    'try', 'catch', 'finally', 'throw', 'new', 'async', 'await', 'true', 'false',
    'null', 'undefined', 'class', 'extends', 'typeof', 'instanceof',
  ]),
  typescript: new Set([
    'function', 'const', 'let', 'var', 'return', 'import', 'export', 'from',
    'default', 'if', 'else', 'for', 'while', 'switch', 'case', 'break', 'continue',
    'try', 'catch', 'finally', 'throw', 'new', 'async', 'await', 'true', 'false',
    'null', 'undefined', 'class', 'extends', 'typeof', 'instanceof', 'interface',
    'type', 'implements', 'readonly', 'as', 'unknown', 'never', 'void', 'string',
    'number', 'boolean',
  ]),
  json: new Set(['true', 'false', 'null']),
  sql: new Set([
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'ON', 'AS',
    'GROUP', 'BY', 'ORDER', 'LIMIT', 'OFFSET', 'INSERT', 'INTO', 'VALUES',
    'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'INDEX', 'AND', 'OR', 'NOT',
    'NULL', 'COUNT', 'AVG', 'SUM', 'DISTINCT', 'DESC', 'ASC',
  ]),
  bash: new Set([
    'if', 'then', 'else', 'fi', 'for', 'do', 'done', 'export', 'cd', 'npm',
    'python', 'pip', 'git', 'curl', 'echo', 'true', 'false',
  ]),
};

const MAX_HIGHLIGHT_CHARS = 12000;

/** Chuan hoa ten ngon ngu tu class language-* cua Markdown code fence. */
export function normalizeCodeLanguage(rawLanguage?: string): string {
  const cleaned = (rawLanguage || '').trim().toLowerCase();
  if (!cleaned) return '';
  return LANGUAGE_ALIASES[cleaned] || cleaned;
}

/** Tach ma nguon thanh cac token to sang cu phap nhe theo tuyen tinh O(n). */
export function tokenizeCode(code: string, rawLanguage?: string): SyntaxToken[] {
  if (!code) return [];
  const lang = normalizeCodeLanguage(rawLanguage);
  const keywords = KEYWORDS_BY_LANG[lang];
  if (!keywords || code.length > MAX_HIGHLIGHT_CHARS) {
    return [{ kind: 'plain', value: code }];
  }

  const hashComments = lang === 'python' || lang === 'bash';
  const slashComments = lang === 'javascript' || lang === 'typescript';
  const dashComments = lang === 'sql';
  const caseInsensitiveKw = lang === 'sql';

  const patternParts: string[] = [];
  if (hashComments) patternParts.push('#[^\\n]*');
  if (slashComments) patternParts.push('\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/');
  if (dashComments) patternParts.push('--[^\\n]*');

  // Strings (single, double, template), numbers, identifiers
  patternParts.push('"(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\'|`(?:\\\\.|[^`\\\\])*`');
  patternParts.push('\\b\\d+(?:\\.\\d+)?\\b');
  patternParts.push('\\b[A-Za-z_][A-Za-z0-9_]*\\b');

  const regex = new RegExp(patternParts.join('|'), 'g');
  const tokens: SyntaxToken[] = [];
  let lastIndex = 0;

  let match: RegExpExecArray | null = regex.exec(code);
  while (match !== null) {
    const start = match.index;
    if (start > lastIndex) {
      tokens.push({ kind: 'plain', value: code.slice(lastIndex, start) });
    }

    const lexeme = match[0];
    let kind: SyntaxTokenKind = 'plain';

    if (
      (hashComments && lexeme.startsWith('#')) ||
      (slashComments && (lexeme.startsWith('//') || lexeme.startsWith('/*'))) ||
      (dashComments && lexeme.startsWith('--'))
    ) {
      kind = 'comment';
    } else if (lexeme.startsWith('"') || lexeme.startsWith("'") || lexeme.startsWith('`')) {
      kind = 'string';
    } else if (/^\d/.test(lexeme)) {
      kind = 'number';
    } else {
      const lookup = caseInsensitiveKw ? lexeme.toUpperCase() : lexeme;
      if (keywords.has(lookup)) {
        kind = 'keyword';
      }
    }

    tokens.push({ kind, value: lexeme });
    lastIndex = start + lexeme.length;
    match = regex.exec(code);
  }

  if (lastIndex < code.length) {
    tokens.push({ kind: 'plain', value: code.slice(lastIndex) });
  }

  return tokens;
}
