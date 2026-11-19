import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  ALL_SECTIONS,
  EMPTY_SUMMARY,
  PERIOD_SCOPED_SECTIONS,
  createEmptySnapshot,
  createQueryPeriodDescriptor,
  createSectionStatusMap,
  hasSamePeriodQueryScope,
  isSameCalendarPeriod,
  isStaleDashboardResponse,
  resetPeriodScopedSnapshot,
  resolveActivePeriodAfterSync,
  resolvePeriodFromServerList,
  resolveTimeFilterForPeriod,
} from '../src/hooks/dashboardDataState.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const SRC_DIR = path.join(FRONTEND_DIR, 'src');

describe('Phase 2 - Dashboard Data State & Race Condition Guard', () => {
  it('detects stale or aborted responses accurately', () => {
    assert.equal(
      isStaleDashboardResponse({ activeRequestId: 2, requestId: 1, aborted: false }),
      true
    );
    assert.equal(
      isStaleDashboardResponse({ activeRequestId: 2, requestId: 2, aborted: true }),
      true
    );
    assert.equal(
      isStaleDashboardResponse({ activeRequestId: 2, requestId: 2, aborted: false }),
      false
    );
  });

  it('discards out-of-order slower responses when AbortController cancels prior fetch', async () => {
    let activeReqId = 0;
    let appliedValue = 'none';

    const simulateFetch = async (label: string, delayMs: number, controller: AbortController) => {
      const reqId = ++activeReqId;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      if (isStaleDashboardResponse({ activeRequestId: activeReqId, requestId: reqId, aborted: controller.signal.aborted })) {
        return;
      }
      appliedValue = label;
    };

    const c1 = new AbortController();
    const p1 = simulateFetch('week', 40, c1);
    c1.abort();

    const c2 = new AbortController();
    const p2 = simulateFetch('month', 5, c2);

    await Promise.all([p1, p2]);
    assert.equal(appliedValue, 'month');
  });

  it('clears period-scoped metrics while preserving rolling persona and recent history', () => {
    const base = createEmptySnapshot();
    base.summary = { ...EMPTY_SUMMARY, total_plays: 120 };
    base.topTracks = [{ spotify_id: 't1', name: 'Song', album_name: 'Alb', album_image_url: '', artists: ['A'], play_count: 5 }];
    base.persona = {
      period_type: 'monthly',
      persona_title: 'Night Owl',
      tagline: 'Late night vibe',
      vibe_summary: 'Summary',
      mood_distribution: { chill: 80 },
      ai_advice: 'Keep listening',
    };
    base.recentScrobbles = [
      {
        id: 1,
        played_at: '2026-10-01T10:00:00Z',
        created_at: '2026-10-01T10:01:00Z',
        context_type: 'playlist',
        track: {
          spotify_id: 't1',
          name: 'Song',
          duration_ms: 180000,
          album: { spotify_id: 'a1', name: 'Alb', image_url: '' },
          artists: [{ spotify_id: 'ar1', name: 'A' }],
        },
      },
    ];

    const reset = resetPeriodScopedSnapshot(base);
    assert.equal(reset.summary.total_plays, 0);
    assert.equal(reset.topTracks.length, 0);
    assert.equal(reset.persona?.persona_title, 'Night Owl');
    assert.equal(reset.recentScrobbles.length, 1);
  });

  it('normalizes month calendar bounds if range spans more than 32 days', () => {
    const filter = resolveTimeFilterForPeriod(
      {
        key: '2026-10',
        label: 'Tháng 10/2026',
        start_date: '2026-09-20',
        end_date: '2026-10-31',
        is_current: true,
        play_count: 10,
      },
      'month'
    );
    assert.deepEqual(filter, { start_date: '2026-10-01', end_date: '2026-10-31' });
  });

  it('creates isolated per-section status maps for partial failure resilience', () => {
    const map = createSectionStatusMap(PERIOD_SCOPED_SECTIONS);
    assert.equal(Object.keys(map).length, ALL_SECTIONS.length);
    assert.equal(map.radar.loading, true);
    assert.equal(map.history.loading, false);
    assert.equal(map.persona.loading, false);
  });

  it('preserves period object identity and query scope across identical server syncs', () => {
    const mockMonth = {
      key: '2026-11',
      label: 'Tháng 11/2026',
      start_date: '2026-11-01',
      end_date: '2026-11-30',
      is_current: true,
      play_count: 685,
    };
    const identicalClone = { ...mockMonth };
    const updatedCountMonth = { ...mockMonth, play_count: 142 };
    const nextMonth = {
      key: '2026-12',
      label: 'Tháng 12/2026',
      start_date: '2026-12-01',
      end_date: '2026-12-31',
      is_current: true,
      play_count: 10,
    };

    assert.equal(isSameCalendarPeriod(mockMonth, identicalClone), true);
    assert.equal(isSameCalendarPeriod(mockMonth, updatedCountMonth), false);
    assert.equal(hasSamePeriodQueryScope(mockMonth, updatedCountMonth), true);
    assert.equal(hasSamePeriodQueryScope(mockMonth, nextMonth), false);
    assert.equal(hasSamePeriodQueryScope(null, mockMonth), false);

    assert.equal(resolvePeriodFromServerList(mockMonth, [identicalClone], 'current', null), mockMonth);
    assert.equal(resolvePeriodFromServerList(mockMonth, [], 'current', null), mockMonth);

    const serverResolved = resolvePeriodFromServerList(mockMonth, [updatedCountMonth], 'current', null);
    assert.equal(serverResolved, updatedCountMonth);
    assert.equal(hasSamePeriodQueryScope(mockMonth, serverResolved), true);

    assert.equal(resolvePeriodFromServerList(mockMonth, [updatedCountMonth, nextMonth], 'specific', '2026-12'), nextMonth);
    assert.equal(resolveActivePeriodAfterSync(mockMonth, [identicalClone]), mockMonth);
    assert.equal(resolveActivePeriodAfterSync(null, [updatedCountMonth]), updatedCountMonth);
    assert.equal(createQueryPeriodDescriptor('', '2026-11-01', '2026-11-30'), null);
    assert.equal(createQueryPeriodDescriptor('2026-11', '2026-11-01', '2026-11-30')?.key, '2026-11');
  });

  it('guards useDashboardData, useDashboardPeriod, and useSpotifySync against redundant abort double-fetch', () => {
    const dataHook = fs.readFileSync(path.join(SRC_DIR, 'hooks', 'useDashboardData.ts'), 'utf-8');
    const periodHook = fs.readFileSync(path.join(SRC_DIR, 'hooks', 'useDashboardPeriod.ts'), 'utf-8');
    const syncHook = fs.readFileSync(path.join(SRC_DIR, 'hooks', 'useSpotifySync.ts'), 'utf-8');

    assert.ok(dataHook.includes('createQueryPeriodDescriptor'));
    assert.ok(dataHook.includes('[periodKey, periodStartDate, periodEndDate]'));
    assert.ok(dataHook.includes('[user, periodType, queryPeriod, refreshAllData]'));

    assert.ok(periodHook.includes('resolvePeriodFromServerList'));
    assert.ok(periodHook.includes('isSameCalendarPeriod'));

    assert.ok(syncHook.includes('resolveActivePeriodAfterSync'));
    assert.ok(syncHook.includes('hasSamePeriodQueryScope'));
  });
});

describe('Phase 2 - Design System, Accessibility & Responsive Contracts', () => {
  it('sets Vietnamese HTML lang and MusicTrack title in index.html', () => {
    const html = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf-8');
    assert.match(html, /<html\s+lang="vi"/);
    assert.match(html, /<title>MusicTrack/);
  });

  it('defines @theme tokens, keyframes, and prefers-reduced-motion in index.css', () => {
    const css = fs.readFileSync(path.join(SRC_DIR, 'index.css'), 'utf-8');
    for (const token of [
      '--color-obsidian-bg',
      '--color-obsidian-card',
      '--color-obsidian-elevated',
      '--color-obsidian-border',
      '--color-spotify-green',
      '@keyframes mtFadeIn',
      '@keyframes mtSlideUp',
      'prefers-reduced-motion: reduce',
    ]) {
      assert.ok(css.includes(token), `Missing token or animation rule: ${token}`);
    }
  });

  it('removes dead tailwindcss-animate classes across components', () => {
    const collectFiles = (dir: string): string[] => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      const files: string[] = [];
      for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          files.push(...collectFiles(full));
        } else if (entry.name.endsWith('.tsx')) {
          files.push(full);
        }
      }
      return files;
    };

    for (const file of collectFiles(SRC_DIR)) {
      const content = fs.readFileSync(file, 'utf-8');
      assert.equal(
        /\banimate-in\b|\bslide-in-from-/.test(content),
        false,
        `Found unsupported animation class in ${path.relative(FRONTEND_DIR, file)}`
      );
    }
  });

  it('ensures ListeningHeatmap supports tap/click, keyboard buttons, aria-pressed, and empty state', () => {
    const heatmap = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'charts', 'ListeningHeatmap.tsx'),
      'utf-8'
    );
    assert.ok(heatmap.includes('<button'));
    assert.ok(heatmap.includes('aria-pressed={isSelected}'));
    assert.ok(heatmap.includes('SectionEmptyState'));
    assert.ok(heatmap.includes('SectionErrorState'));
  });

  it('ensures CalendarPeriodSelector uses viewport-safe dropdown positioning and Escape handling', () => {
    const selector = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'ui', 'CalendarPeriodSelector.tsx'),
      'utf-8'
    );
    assert.ok(selector.includes('left-0 sm:left-auto sm:right-0'));
    assert.ok(selector.includes('calc(100vw-1.5rem)'));
    assert.ok(selector.includes("event.key === 'Escape'"));
  });

  it('places Assistant at bottom of dashboard and removes raw colors/tech stack from Footer', () => {
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8');
    const scrobblesPos = app.indexOf('<RecentScrobblesList');
    const assistantPos = app.indexOf('<CodebaseAssistantSection');
    assert.ok(scrobblesPos > 0 && assistantPos > scrobblesPos);
    assert.ok(!app.includes('#0B0F17'));
    assert.ok(!app.includes('Tailwind v4'));
    assert.ok(app.includes('hasAutoSyncedRef'));
  });
});
