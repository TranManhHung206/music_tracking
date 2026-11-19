import type {
  CalendarPeriodType,
  CalendarPeriodItem,
  SummaryStats,
  TopTrack,
  TopArtist,
  TopAlbum,
  RadarData,
  HeatmapData,
  WeeklyComparisonData,
  GenreDistributionData,
  ListeningHistoryRecord,
} from '../types/analytics';
import type { AIMusicPersona, MusicFact, AgentMeta } from '../types/ai';
import type { TimeFilterInput } from '../services/api';

export type SectionKey =
  | 'summary'
  | 'topTracks'
  | 'topArtists'
  | 'topAlbums'
  | 'radar'
  | 'heatmap'
  | 'comparison'
  | 'genres'
  | 'persona'
  | 'history'
  | 'facts';

export interface SectionStatus {
  loading: boolean;
  error: string | null;
}

export type SectionStatusMap = Record<SectionKey, SectionStatus>;

export const PERIOD_SCOPED_SECTIONS: SectionKey[] = [
  'summary',
  'topTracks',
  'topArtists',
  'topAlbums',
  'radar',
  'heatmap',
  'comparison',
  'genres',
  'facts',
];

export const ALL_SECTIONS: SectionKey[] = [
  ...PERIOD_SCOPED_SECTIONS,
  'persona',
  'history',
];

export const EMPTY_SUMMARY: SummaryStats = {
  total_plays: 0,
  total_duration_ms: 0,
  total_hours: 0,
  unique_artists_count: 0,
  unique_albums_count: 0,
  unique_tracks_count: 0,
  time_range: 'week',
};

export const EMPTY_RADAR: RadarData = {
  time_range: 'week',
  total_tracks_analyzed: 0,
  features: [],
};

export const EMPTY_HEATMAP: HeatmapData = {
  time_range: 'week',
  period_type: 'week',
  max_density: 0,
  matrix: [],
};

export const EMPTY_WEEKLY_COMPARISON: WeeklyComparisonData = {
  time_range: 'week',
  period_type: 'week',
  granularity: 'day',
  current_week_label: '',
  previous_week_label: '',
  days: [],
  summary: {
    total_current: 0,
    total_previous: 0,
    total_current_week: 0,
    total_previous_week: 0,
    growth_percentage: 0,
    baseline_status: 'empty',
    peak_day_current: '',
    peak_plays_current: 0,
  },
};

export const EMPTY_GENRES: GenreDistributionData = {
  genres: [],
  total_plays: 0,
  top_genre: 'Chưa có dữ liệu',
};

export interface DashboardDataSnapshot {
  summary: SummaryStats;
  topTracks: TopTrack[];
  topArtists: TopArtist[];
  topAlbums: TopAlbum[];
  radarData: RadarData;
  heatmapData: HeatmapData;
  weeklyComparison: WeeklyComparisonData;
  genreData: GenreDistributionData;
  persona: AIMusicPersona | null;
  recentScrobbles: ListeningHistoryRecord[];
  musicFacts: MusicFact[];
  agentMeta: AgentMeta | undefined;
}

export function createEmptySnapshot(): DashboardDataSnapshot {
  return {
    summary: EMPTY_SUMMARY,
    topTracks: [],
    topArtists: [],
    topAlbums: [],
    radarData: EMPTY_RADAR,
    heatmapData: EMPTY_HEATMAP,
    weeklyComparison: EMPTY_WEEKLY_COMPARISON,
    genreData: EMPTY_GENRES,
    persona: null,
    recentScrobbles: [],
    musicFacts: [],
    agentMeta: undefined,
  };
}

export function createSectionStatusMap(loadingKeys: SectionKey[] = []): SectionStatusMap {
  const loadingSet = new Set<SectionKey>(loadingKeys);
  const map = {} as SectionStatusMap;
  for (const key of ALL_SECTIONS) {
    map[key] = {
      loading: loadingSet.has(key),
      error: null,
    };
  }
  return map;
}

/** Chuẩn hóa tham số start_date / end_date khi chuyển kỳ Tuần / Tháng / Năm. */
export function resolveTimeFilterForPeriod(
  period: CalendarPeriodItem | null,
  periodType: CalendarPeriodType
): TimeFilterInput {
  if (!period) return '30d';
  if (periodType === 'month' && period.start_date && period.end_date) {
    const s = new Date(period.start_date);
    const e = new Date(period.end_date);
    const diffDays = Math.round((e.getTime() - s.getTime()) / (1000 * 3600 * 24));
    if (diffDays > 32) {
      const y = e.getFullYear();
      const m = (e.getMonth() + 1).toString().padStart(2, '0');
      const lastD = new Date(y, e.getMonth() + 1, 0).getDate().toString().padStart(2, '0');
      return { start_date: `${y}-${m}-01`, end_date: `${y}-${m}-${lastD}` };
    }
  }
  return { start_date: period.start_date, end_date: period.end_date };
}

export interface RaceGuardState {
  activeRequestId: number;
  requestId: number;
  aborted: boolean;
}

export function isStaleDashboardResponse(guard: RaceGuardState): boolean {
  return guard.aborted || guard.requestId !== guard.activeRequestId;
}

/** Reset chỉ các khối phụ thuộc khung thời gian để tránh hiển thị nhầm số liệu kỳ cũ khi đang tải kỳ mới. */
export function resetPeriodScopedSnapshot(prev: DashboardDataSnapshot): DashboardDataSnapshot {
  return {
    ...prev,
    summary: EMPTY_SUMMARY,
    topTracks: [],
    topArtists: [],
    topAlbums: [],
    radarData: EMPTY_RADAR,
    heatmapData: EMPTY_HEATMAP,
    weeklyComparison: EMPTY_WEEKLY_COMPARISON,
    genreData: EMPTY_GENRES,
    musicFacts: [],
    agentMeta: undefined,
  };
}

/** Kiểm tra hai đối tượng CalendarPeriodItem có đồng nhất toàn bộ thuộc tính hiển thị hay không. */
export function isSameCalendarPeriod(
  a: CalendarPeriodItem | null | undefined,
  b: CalendarPeriodItem | null | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.key === b.key &&
    a.label === b.label &&
    a.start_date === b.start_date &&
    a.end_date === b.end_date &&
    a.is_current === b.is_current &&
    a.play_count === b.play_count
  );
}

/** Kiểm tra hai kỳ có cùng phạm vi truy vấn API (key, start_date, end_date). */
export function hasSamePeriodQueryScope(
  a: CalendarPeriodItem | null | undefined,
  b: CalendarPeriodItem | null | undefined
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.key === b.key &&
    a.start_date === b.start_date &&
    a.end_date === b.end_date
  );
}

/** Tạo descriptor tối giản chỉ phụ thuộc key và biên ngày cho lệnh gọi API. */
export function createQueryPeriodDescriptor(
  key: string,
  startDate: string,
  endDate: string
): CalendarPeriodItem | null {
  if (!key) return null;
  return {
    key,
    label: key,
    start_date: startDate,
    end_date: endDate,
    is_current: false,
    play_count: 0,
  };
}

/** Chọn lại kỳ phù hợp từ danh sách máy chủ và giữ nguyên tham chiếu cũ nếu dữ liệu giống hệt. */
export function resolvePeriodFromServerList(
  prev: CalendarPeriodItem | null,
  periods: CalendarPeriodItem[],
  savedMode: string | null,
  savedKey: string | null
): CalendarPeriodItem | null {
  if (!Array.isArray(periods) || periods.length === 0) {
    return prev;
  }

  let nextPeriod: CalendarPeriodItem | undefined;
  if (savedMode === 'specific' && savedKey) {
    nextPeriod = periods.find((p) => p.key === savedKey);
  }
  if (!nextPeriod && prev && !prev.is_current && savedMode === 'specific') {
    nextPeriod = periods.find((p) => p.key === prev.key);
  }
  if (!nextPeriod) {
    nextPeriod = periods.find((p) => p.is_current) || periods[0];
  }
  if (!nextPeriod) {
    return prev;
  }
  return prev && isSameCalendarPeriod(prev, nextPeriod) ? prev : nextPeriod;
}

/** Xác định kỳ hiện hành sau đồng bộ Spotify và giữ nguyên tham chiếu nếu không đổi. */
export function resolveActivePeriodAfterSync(
  current: CalendarPeriodItem | null,
  updatedPeriods: CalendarPeriodItem[]
): CalendarPeriodItem | null {
  if (!Array.isArray(updatedPeriods) || updatedPeriods.length === 0) {
    return current;
  }
  const matched = current
    ? updatedPeriods.find((p) => p.key === current.key)
    : undefined;
  const candidate = matched || updatedPeriods[0] || null;
  if (!candidate) {
    return current;
  }
  return current && isSameCalendarPeriod(current, candidate) ? current : candidate;
}
