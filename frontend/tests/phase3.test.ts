import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  formatListeningDuration,
  getListeningFrequencyLabel,
  isRealSpotifyId,
} from '../src/utils/analyticsFormatters.ts';
import { getDemoSnapshotForPeriod } from '../src/services/demoData.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..', 'src');

describe('Phase 3 - Formatters & ShareableCard Frequency Logic', () => {
  it('formats listening duration in minutes below 1 hour and hours above', () => {
    assert.equal(formatListeningDuration(0, 0), '0 giờ');
    assert.equal(formatListeningDuration(24 * 60 * 1000, 0.4), '24 phút');
    assert.equal(formatListeningDuration(90 * 60 * 1000, 1.5), '1.5 giờ');
  });

  it('computes dynamic listening frequency labels per periodType and play count', () => {
    assert.equal(getListeningFrequencyLabel(0, 'week'), 'Chưa ghi nhận');
    assert.equal(getListeningFrequencyLabel(10, 'week'), 'Nhẹ nhàng');
    assert.equal(getListeningFrequencyLabel(35, 'week'), 'Đều đặn');
    assert.equal(getListeningFrequencyLabel(95, 'week'), 'Sôi nổi');
    assert.equal(getListeningFrequencyLabel(220, 'week'), 'Cuồng nhiệt');

    assert.equal(getListeningFrequencyLabel(450, 'month'), 'Bất tận');
    assert.equal(getListeningFrequencyLabel(2500, 'year'), 'Bất tận');
  });

  it('validates real Spotify IDs vs demo/mock placeholders safely', () => {
    assert.equal(isRealSpotifyId('mock_1'), false);
    assert.equal(isRealSpotifyId('art_1'), false);
    assert.equal(isRealSpotifyId('alb_3'), false);
    assert.equal(isRealSpotifyId('demo_track'), false);
    assert.equal(isRealSpotifyId('4iV5W9uYEdYUVa79Axb7Rh'), true);
  });
});

describe('Phase 3 - Synchronized Demo Mode Across Week / Month / Year', () => {
  it('synchronizes Week current & empty historical snapshots consistently', () => {
    const currWeek = getDemoSnapshotForPeriod(
      {
        key: '2026-W46',
        label: 'Tuần này',
        start_date: '2026-11-09',
        end_date: '2026-11-15',
        is_current: true,
        play_count: 311,
      },
      'week'
    );
    assert.equal(currWeek.summary.total_plays, 311);
    assert.equal(currWeek.weeklyComparison.period_type, 'week');
    assert.equal(currWeek.weeklyComparison.summary.total_current, 311);
    assert.equal(currWeek.genreData.total_plays, 311);
    assert.ok(currWeek.heatmapData.matrix.length > 0);

    const emptyWeek = getDemoSnapshotForPeriod(
      {
        key: '2026-W44',
        label: 'Tuần 44',
        start_date: '2026-10-26',
        end_date: '2026-11-01',
        is_current: false,
        play_count: 0,
      },
      'week'
    );
    assert.equal(emptyWeek.summary.total_plays, 0);
    assert.equal(emptyWeek.topTracks.length, 0);
    assert.equal(emptyWeek.genreData.genres.length, 0);
    assert.equal(emptyWeek.weeklyComparison.summary.baseline_status, 'empty');
  });

  it('synchronizes Month current and historical zero-baseline periods accurately', () => {
    const currMonth = getDemoSnapshotForPeriod(
      {
        key: '2026-11',
        label: 'Tháng 11/2026',
        start_date: '2026-11-01',
        end_date: '2026-11-30',
        is_current: true,
        play_count: 685,
      },
      'month'
    );
    assert.equal(currMonth.summary.total_plays, 685);
    assert.equal(currMonth.weeklyComparison.period_type, 'month');
    assert.equal(currMonth.weeklyComparison.granularity, 'week_of_month');
    assert.equal(currMonth.heatmapData.month_calendar?.year, 2026);
    assert.equal(currMonth.heatmapData.month_calendar?.month, 11);
    assert.equal(currMonth.heatmapData.month_calendar?.total_plays, 685);

    const prevMonth = getDemoSnapshotForPeriod(
      {
        key: '2026-10',
        label: 'Tháng 10/2026',
        start_date: '2026-10-01',
        end_date: '2026-10-31',
        is_current: false,
        play_count: 540,
      },
      'month'
    );
    assert.equal(prevMonth.weeklyComparison.summary.baseline_status, 'new_activity');
    assert.equal(prevMonth.weeklyComparison.summary.growth_percentage, null);
  });

  it('synchronizes Year snapshots with 12-month series and 53-week calendar', () => {
    const currYear = getDemoSnapshotForPeriod(
      {
        key: '2026',
        label: 'Năm 2026',
        start_date: '2026-01-01',
        end_date: '2026-12-31',
        is_current: true,
        play_count: 2840,
      },
      'year'
    );
    assert.equal(currYear.summary.total_plays, 2840);
    assert.equal(currYear.weeklyComparison.period_type, 'year');
    assert.equal(currYear.weeklyComparison.series?.length, 12);
    assert.equal(currYear.heatmapData.year_calendar?.year, 2026);
    assert.equal(currYear.heatmapData.year_calendar?.total_plays, 2840);
  });
});

describe('Phase 3 - Information Architecture & Visualization UX Contracts', () => {
  it('orders App.tsx sections from KPI -> Trend -> Heatmap -> Taste -> Charts -> AI -> History -> Assistant', () => {
    const app = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8');
    const markers = [
      '<StatCard',
      '<WeeklyComparisonChart',
      '<ListeningHeatmap',
      '<RadarChartComponent',
      '<GenreDistribution',
      '<TopTracksList',
      '<PersonaCard',
      '<MusicFactsSection',
      '<RecentScrobblesList',
      '<CodebaseAssistantSection',
    ];
    let lastPos = -1;
    for (const marker of markers) {
      const pos = app.indexOf(marker);
      assert.ok(pos > lastPos, `Expected ${marker} to appear after previous section`);
      lastPos = pos;
    }
  });

  it('implements special 100% single-genre card and honest classifier note in GenreDistribution', () => {
    const code = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'charts', 'GenreDistribution.tsx'),
      'utf-8'
    );
    assert.ok(code.includes('genres.length === 1'));
    assert.ok(code.includes('Thể loại thống trị duy nhất'));
    assert.ok(code.includes('MusicTrack'));
  });

  it('enforces consistent Radar axis ordering and accessible textual summary', () => {
    const code = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'charts', 'RadarChartComponent.tsx'),
      'utf-8'
    );
    assert.ok(code.includes('AXIS_ORDER'));
    assert.ok(code.includes('Nổi bật nhất:'));
    assert.ok(code.includes('RadarCustomTooltip'));
  });

  it('uses dynamic listening frequency label instead of hardcoded Soi noi in ShareableCard', () => {
    const code = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'cards', 'ShareableCard.tsx'),
      'utf-8'
    );
    assert.ok(code.includes('getListeningFrequencyLabel'));
    assert.equal(code.includes('>Sôi nổi<'), false);
  });
});
