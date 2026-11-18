import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildDemoAssistantReply } from '../src/services/demoData.ts';
import type { AssistantEvidenceItem } from '../src/types/ai.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..', 'src');

describe('Phase 4 - Hybrid Music & Website Assistant Demo & Routing Contracts', () => {
  const sampleWeek = {
    key: '2026-W46',
    label: 'Tuần này',
    start_date: '2026-11-09',
    end_date: '2026-11-15',
    is_current: true,
    play_count: 311,
  };

  it('routes personal music queries to music_insights synced with active period', () => {
    const res = buildDemoAssistantReply(
      'Trong tuần này tôi nghe bài hát và nghệ sĩ nào nhiều nhất?',
      'auto',
      sampleWeek,
      'week',
      0
    );
    assert.equal(res.resolved_domain, 'music_insights');
    assert.equal(res.needs_clarification, false);
    assert.equal(res.scope.label, 'Tuần này');
    assert.ok(res.answer.includes('311'));
    assert.ok(res.evidence.some((e: AssistantEvidenceItem) => e.is_estimate));
  });

  it('routes website mechanism queries to website_support with friendly topics and no file paths', () => {
    const res = buildDemoAssistantReply(
      'Thông tin tài khoản Spotify và token của tôi được bảo vệ như thế nào?',
      'auto',
      sampleWeek,
      'week',
      0
    );
    assert.equal(res.resolved_domain, 'website_support');
    assert.equal(res.needs_clarification, false);
    assert.ok(res.topics.length >= 1);
    assert.equal(res.answer.includes('backend/'), false);
    assert.equal(res.answer.includes('[S1]'), false);
  });

  it('returns clarification gate on ambiguous query in auto mode', () => {
    const res = buildDemoAssistantReply('Giải thích giúp tôi', 'auto', sampleWeek, 'week', 0);
    assert.equal(res.resolved_domain, 'clarification');
    assert.equal(res.needs_clarification, true);
    assert.equal(res.clarification_options.length, 2);
  });

  it('handles empty zero-play period honestly without fabricating listening data', () => {
    const emptyWeek = {
      key: '2026-W44',
      label: 'Tuần 44',
      start_date: '2026-10-26',
      end_date: '2026-11-01',
      is_current: false,
      play_count: 0,
    };
    const res = buildDemoAssistantReply('Tổng kết lượt phát của tôi', 'music_insights', emptyWeek, 'week', 0);
    assert.equal(res.resolved_domain, 'music_insights');
    assert.ok(res.answer.includes('0 lượt phát'));
  });
});

describe('Phase 4 - MusicTrack Assistant UI & Security Contracts', () => {
  it('upgrades CodebaseAssistantSection to MusicTrack Assistant with 3 modes, clear session, and admin gates', () => {
    const code = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'analytics', 'CodebaseAssistantSection.tsx'),
      'utf-8'
    );
    assert.ok(code.includes('MusicTrack Assistant'));
    assert.ok(code.includes("id: 'auto'"));
    assert.ok(code.includes("id: 'music_insights'"));
    assert.ok(code.includes("id: 'website_support'"));
    assert.ok(code.includes('SAMPLE_QUERIES_BY_MODE'));
    assert.ok(code.includes('Xóa hội thoại'));
    assert.ok(code.includes('SectionErrorState'));
    assert.ok(code.includes('isAdmin &&'));
    assert.ok(code.includes('queryAssistant'));
    assert.ok(code.includes('clearAssistantSession'));
    assert.equal(code.includes('useEffect'), false);
  });

  it('isolates assistant instance by demo/user key in App.tsx and exposes typed API methods', () => {
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8');
    const apiCode = fs.readFileSync(path.join(SRC_DIR, 'services', 'api.ts'), 'utf-8');
    assert.ok(app.includes("auth-assistant-"));
    assert.ok(app.includes('selectedPeriod={selectedPeriod}'));
    assert.ok(apiCode.includes('/api/ai/assistant/query/'));
    assert.ok(apiCode.includes('/api/ai/assistant/session/clear/'));
  });
});
