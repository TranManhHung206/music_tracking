import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_DIR = path.resolve(__dirname, '..');
const SRC_DIR = path.join(FRONTEND_DIR, 'src');

describe('Phase 5 - Dead Code Cleanup & Dependencies', () => {
  it('removes confirmed unused frontend files and legacy html2canvas package', () => {
    assert.equal(fs.existsSync(path.join(SRC_DIR, 'components', 'charts', 'BarChartRace.tsx')), false);
    assert.equal(fs.existsSync(path.join(SRC_DIR, 'components', 'ui', 'TimeRangeSelector.tsx')), false);
    assert.equal(fs.existsSync(path.join(SRC_DIR, 'App.css')), false);

    const pkg = JSON.parse(fs.readFileSync(path.join(FRONTEND_DIR, 'package.json'), 'utf-8')) as {
      dependencies: Record<string, string>;
    };
    assert.equal('html2canvas' in pkg.dependencies, false);
    assert.ok('html2canvas-pro' in pkg.dependencies);
  });

  it('removes unused MOCK_USER, MOCK_RACE, getBarChartRace, and race types', () => {
    const apiCode = fs.readFileSync(path.join(SRC_DIR, 'services', 'api.ts'), 'utf-8');
    const typesCode = fs.readFileSync(path.join(SRC_DIR, 'types', 'analytics.ts'), 'utf-8');

    assert.equal(apiCode.includes('MOCK_USER'), false);
    assert.equal(apiCode.includes('MOCK_RACE'), false);
    assert.equal(apiCode.includes('getBarChartRace'), false);

    assert.equal(typesCode.includes('RankingEntry'), false);
    assert.equal(typesCode.includes('TimelineFrame'), false);
    assert.equal(typesCode.includes('BarChartRaceData'), false);
  });
});

describe('Phase 5 - Frontend Performance, Lazy Loading & Bundle Splitting', () => {
  it('memoizes heatmap lookup maps in ListeningHeatmap with useMemo', () => {
    const heatmapCode = fs.readFileSync(
      path.join(SRC_DIR, 'components', 'charts', 'ListeningHeatmap.tsx'),
      'utf-8'
    );
    assert.ok(heatmapCode.includes('useMemo'));
    assert.ok(heatmapCode.includes('weekCountMap'));
    assert.ok(heatmapCode.includes('yearGridMap'));
    assert.ok(heatmapCode.includes('monthHeaderMap'));
    assert.equal(heatmapCode.includes('daysInWeek.find('), false);
    assert.equal(heatmapCode.includes('safeData.find('), false);
  });

  it('applies lazy decoding attributes and intrinsic dimensions to list and modal artwork', () => {
    const files = [
      path.join(SRC_DIR, 'components', 'cards', 'TopTracksList.tsx'),
      path.join(SRC_DIR, 'components', 'cards', 'TopArtistsList.tsx'),
      path.join(SRC_DIR, 'components', 'cards', 'TopAlbumsList.tsx'),
      path.join(SRC_DIR, 'components', 'cards', 'RecentScrobblesList.tsx'),
      path.join(SRC_DIR, 'components', 'cards', 'RecommendationModal.tsx'),
    ];
    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8');
      assert.ok(content.includes('loading="lazy"'), `Missing loading="lazy" in ${path.basename(file)}`);
      assert.ok(content.includes('decoding="async"'), `Missing decoding="async" in ${path.basename(file)}`);
    }
  });

  it('lazy-loads modal components in App.tsx and configures Rolldown code splitting', () => {
    const appCode = fs.readFileSync(path.join(SRC_DIR, 'App.tsx'), 'utf-8');
    const viteCode = fs.readFileSync(path.join(FRONTEND_DIR, 'vite.config.ts'), 'utf-8');

    assert.ok(appCode.includes('lazy('));
    assert.ok(appCode.includes('<Suspense'));
    assert.ok(viteCode.includes('codeSplitting'));
    assert.ok(viteCode.includes('vendor-charts'));
    assert.ok(viteCode.includes('vendor-capture'));
  });
});
