import axios, { AxiosError } from 'axios';
import type { UserProfile, SpotifyExchangeResponse } from '../types/auth';
import type {
  TimeRange,
  SummaryStats,
  TopTrack,
  TopArtist,
  TopAlbum,
  RadarData,
  HeatmapData,
  MonthHeatmapData,
  YearHeatmapData,
  WeeklyComparisonData,
  GenreDistributionData,
  ListeningHistoryRecord,
  CalendarPeriodType,
  CalendarPeriodItem,
} from '../types/analytics';
import type {
  AIMusicPersona,
  RecommendationResult,
  MusicFactsResponse,
  CodebaseQueryResponse,
  CodebaseQueryPayload,
  AssistantQueryPayload,
  AssistantQueryResponse,
} from '../types/ai';

export type TimeFilterInput = TimeRange | { time_range?: string; start_date?: string; end_date?: string };

function buildTimeParams(filter?: TimeFilterInput): string {
  if (!filter) return 'time_range=30d';
  if (typeof filter === 'string') return `time_range=${filter}`;
  const parts: string[] = [];
  if (filter.time_range) parts.push(`time_range=${filter.time_range}`);
  if (filter.start_date) parts.push(`start_date=${filter.start_date}`);
  if (filter.end_date) parts.push(`end_date=${filter.end_date}`);
  return parts.length > 0 ? parts.join('&') : 'time_range=30d';
}

export class ApiError extends Error {
  status?: number;
  retryAfterSeconds?: number;

  constructor(message: string, status?: number, retryAfterSeconds?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export function isRequestCanceled(err: unknown): boolean {
  if (axios.isCancel(err)) return true;
  if (err && typeof err === 'object') {
    const obj = err as { name?: string; code?: string };
    return obj.name === 'AbortError' || obj.name === 'CanceledError' || obj.code === 'ERR_CANCELED';
  }
  return false;
}

function toApiError(err: unknown, fallbackMessage: string): ApiError {
  if (err instanceof ApiError) return err;
  if (axios.isAxiosError(err)) {
    const axiosErr = err as AxiosError<{ error?: string; detail?: string; retry_after_seconds?: number }>;
    const status = axiosErr.response?.status;
    const serverMsg = axiosErr.response?.data?.error || axiosErr.response?.data?.detail;
    const retryAfter = axiosErr.response?.data?.retry_after_seconds;

    if (status === 401) {
      return new ApiError('Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.', 401);
    }
    if (status === 403) {
      return new ApiError(serverMsg || 'Bạn không có quyền thực hiện thao tác này.', 403);
    }
    if (status === 404) {
      return new ApiError(
        serverMsg || 'Không tìm thấy endpoint API (404). Nếu Backend vừa cập nhật, vui lòng khởi động lại máy chủ Django.',
        404
      );
    }
    if (status === 429) {
      return new ApiError(
        serverMsg || 'Hệ thống đang bị giới hạn tần suất yêu cầu. Vui lòng thử lại sau.',
        429,
        retryAfter
      );
    }
    if (!axiosErr.response) {
      return new ApiError('Không thể kết nối đến máy chủ Backend. Vui lòng kiểm tra kết nối mạng.', undefined);
    }
    return new ApiError(serverMsg || fallbackMessage, status, retryAfter);
  }
  if (err instanceof Error) {
    return new ApiError(err.message || fallbackMessage);
  }
  return new ApiError(fallbackMessage);
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Token ${token}`;
  }
  const clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Ho_Chi_Minh';
  if (config.headers) {
    config.headers['X-Timezone'] = clientTimezone;
  }
  return config;
});

// Mock Fallback Data de hien thi UI ngay ca khi offline
export const MOCK_SUMMARY: SummaryStats = {
  total_plays: 428,
  total_duration_ms: 102720000,
  total_hours: 28.53,
  unique_artists_count: 64,
  unique_albums_count: 52,
  time_range: '30d',
};

export const MOCK_TOP_TRACKS: TopTrack[] = [
  {
    spotify_id: 'mock_1',
    name: 'Chúng Ta Của Tương Lai',
    album_name: 'Chúng Ta',
    album_image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
    artists: ['Sơn Tùng M-TP'],
    play_count: 48,
  },
  {
    spotify_id: 'mock_2',
    name: 'Nấu Ăn Cho Em',
    album_name: 'Nấu Ăn Cho Em',
    album_image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    artists: ['Đen Vâu', 'PiaLinh'],
    play_count: 36,
  },
  {
    spotify_id: 'mock_3',
    name: 'Từng Là',
    album_name: 'Từng Là',
    album_image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    artists: ['Vũ Cát Tường'],
    play_count: 29,
  },
  {
    spotify_id: 'mock_4',
    name: 'Blinding Lights',
    album_name: 'After Hours',
    album_image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    artists: ['The Weeknd'],
    play_count: 25,
  },
  {
    spotify_id: 'mock_5',
    name: 'Levitating',
    album_name: 'Future Nostalgia',
    album_image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    artists: ['Dua Lipa'],
    play_count: 22,
  },
];

export const MOCK_TOP_ARTISTS: TopArtist[] = [
  {
    spotify_id: 'art_1',
    name: 'Sơn Tùng M-TP',
    image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
    play_count: 86,
  },
  {
    spotify_id: 'art_2',
    name: 'Đen Vâu',
    image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    play_count: 65,
  },
  {
    spotify_id: 'art_3',
    name: 'The Weeknd',
    image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    play_count: 54,
  },
  {
    spotify_id: 'art_4',
    name: 'Vũ Cát Tường',
    image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    play_count: 42,
  },
  {
    spotify_id: 'art_5',
    name: 'Dua Lipa',
    image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    play_count: 38,
  },
];

export const MOCK_RADAR: RadarData = {
  time_range: '30d',
  total_tracks_analyzed: 428,
  features: [
    { attribute: 'valence', score: 0.65, description: 'Tích cực, vui tươi' },
    { attribute: 'energy', score: 0.78, description: 'Sôi động, mạnh mẽ' },
    { attribute: 'danceability', score: 0.72, description: 'Dễ nhảy, nhịp điệu rõ' },
    { attribute: 'acousticness', score: 0.35, description: 'Mộc mạc, ít điện tử' },
    { attribute: 'tempo_normalized', score: 0.62, description: 'Tốc độ nhịp BPM chuẩn hóa' },
  ],
  provenance: {
    spotify: 0,
    dsp_preview: 410,
    estimated: 18,
    legacy_unknown: 0,
    unavailable: 0,
    total_plays: 428,
    measured_percentage: 95.8,
    has_estimates: true,
    has_legacy_unknown: false,
  },
};

export const MOCK_MONTH_CALENDAR: MonthHeatmapData = {
  year: 2026,
  month: 10,
  first_day_weekday: 4,
  total_days: 31,
  total_plays: 248,
  peak_day: '2026-10-10',
  peak_plays: 22,
  active_days: 31,
  max_density: 22,
  days: Array.from({ length: 31 }, (_, i) => {
    const dayNum = i + 1;
    const dateStr = `2026-10-${dayNum.toString().padStart(2, '0')}`;
    const weekday = ((4 + i - 1) % 7) + 1;
    const count = dayNum % 7 === 0 || dayNum % 6 === 0 ? 12 + (i % 9) : 3 + ((i * 2) % 6);
    return {
      date: dateStr,
      day_number: dayNum,
      day_of_week: weekday,
      count,
      is_current_month: true,
    };
  }),
};

export const MOCK_YEAR_CALENDAR: YearHeatmapData = {
  year: 2026,
  total_weeks: 53,
  total_days: 371,
  total_plays: 2840,
  peak_day: '2026-06-18',
  peak_plays: 20,
  active_days: 280,
  longest_streak: 18,
  top_month: 10,
  top_month_plays: 412,
  max_density: 20,
  months_header: [
    { month: 1, label: 'T1', start_week: 0 },
    { month: 2, label: 'T2', start_week: 4 },
    { month: 3, label: 'T3', start_week: 8 },
    { month: 4, label: 'T4', start_week: 13 },
    { month: 5, label: 'T5', start_week: 17 },
    { month: 6, label: 'T6', start_week: 22 },
    { month: 7, label: 'T7', start_week: 26 },
    { month: 8, label: 'T8', start_week: 30 },
    { month: 9, label: 'T9', start_week: 35 },
    { month: 10, label: 'T10', start_week: 39 },
    { month: 11, label: 'T11', start_week: 44 },
    { month: 12, label: 'T12', start_week: 48 },
  ],
  days: Array.from({ length: 53 * 7 }, (_, i) => {
    const weekIndex = Math.floor(i / 7);
    const dayOfWeek = (i % 7) + 1;
    const count = i % 10 === 0 ? 0 : ((i * 3 + 5) % 18) + 1;
    return {
      date: `2026-W${weekIndex + 1}-${dayOfWeek}`,
      month: Math.min(12, Math.floor(weekIndex / 4.4) + 1),
      day_number: (i % 28) + 1,
      day_of_week: dayOfWeek,
      week_index: weekIndex,
      count,
      is_in_range: true,
    };
  }),
};

export const MOCK_HEATMAP: HeatmapData = {
  time_range: '30d',
  period_type: 'week',
  max_density: 18,
  month_calendar: MOCK_MONTH_CALENDAR,
  year_calendar: MOCK_YEAR_CALENDAR,
  matrix: Array.from({ length: 7 * 24 }, (_, i) => {
    const day = Math.floor(i / 24) + 1;
    const hour = i % 24;
    let count = 0;
    if (hour >= 20 && hour <= 23) {
      count = ((day * 3 + hour) % 12) + 4;
    } else if (hour >= 8 && hour <= 18) {
      count = (day + hour) % 8;
    } else if (hour >= 0 && hour <= 2) {
      count = ((day + hour) % 6) + 2;
    }
    return { day_of_week: day, hour, count };
  }),
};

export const MOCK_TOP_ALBUMS: TopAlbum[] = [
  {
    spotify_id: 'alb_1',
    name: 'Chúng Ta',
    image_url: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=300&h=300&fit=crop',
    release_date: '2021',
    artists: ['Sơn Tùng M-TP'],
    play_count: 58,
  },
  {
    spotify_id: 'alb_2',
    name: 'Show Của Đen',
    image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    release_date: '2023',
    artists: ['Đen Vâu'],
    play_count: 46,
  },
  {
    spotify_id: 'alb_3',
    name: 'After Hours',
    image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    release_date: '2020',
    artists: ['The Weeknd'],
    play_count: 39,
  },
  {
    spotify_id: 'alb_4',
    name: 'Inner Me',
    image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    release_date: '2019',
    artists: ['Vũ Cát Tường'],
    play_count: 32,
  },
  {
    spotify_id: 'alb_5',
    name: 'Future Nostalgia',
    image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    release_date: '2020',
    artists: ['Dua Lipa'],
    play_count: 28,
  },
];

export const MOCK_WEEKLY_COMPARISON: WeeklyComparisonData = {
  time_range: '7d',
  period_type: 'week',
  granularity: 'day',
  current_label: 'Tuần này (05/10 - 11/10)',
  previous_label: 'Tuần trước (28/09 - 04/10)',
  current_week_label: 'Tuần này (05/10 - 11/10)',
  previous_week_label: 'Tuần trước (28/09 - 04/10)',
  days: [
    { day_index: 1, day_name: 'Thứ 2', day_name_en: 'Mon', current_week_plays: 28, previous_week_plays: 20, diff: 8 },
    { day_index: 2, day_name: 'Thứ 3', day_name_en: 'Tue', current_week_plays: 42, previous_week_plays: 35, diff: 7 },
    { day_index: 3, day_name: 'Thứ 4', day_name_en: 'Wed', current_week_plays: 35, previous_week_plays: 30, diff: 5 },
    { day_index: 4, day_name: 'Thứ 5', day_name_en: 'Thu', current_week_plays: 48, previous_week_plays: 38, diff: 10 },
    { day_index: 5, day_name: 'Thứ 6', day_name_en: 'Fri', current_week_plays: 65, previous_week_plays: 50, diff: 15 },
    { day_index: 6, day_name: 'Thứ 7', day_name_en: 'Sat', current_week_plays: 55, previous_week_plays: 45, diff: 10 },
    { day_index: 7, day_name: 'Chủ Nhật', day_name_en: 'Sun', current_week_plays: 38, previous_week_plays: 32, diff: 6 },
  ],
  summary: {
    total_current: 311,
    total_previous: 250,
    total_current_week: 311,
    total_previous_week: 250,
    growth_percentage: 24.4,
    baseline_status: 'normal',
    peak_label: 'Thứ 6',
    peak_plays: 65,
    peak_day_current: 'Thứ 6',
    peak_plays_current: 65,
  },
};

export const MOCK_PERSONA: AIMusicPersona = {
  id: 1,
  period_type: 'monthly',
  persona_title: 'The Late-Night Sonic Rebel',
  tagline: 'Đêm khuya, năng lượng bùng nổ và chiều sâu nội tâm đa tầng.',
  vibe_summary:
    'Bạn thường xuyên chìm đắm trong âm nhạc vào khung giờ từ 21:00 đến 01:00 sáng. Gu nghe nhạc của bạn gắn liền với những bản phối sôi động, nhịp bass đầy nội lực từ Sơn Tùng M-TP và The Weeknd, phản chiếu tinh thần sáng tạo mạnh mẽ và cá tính tự do.',
  mood_distribution: {
    energetic: 45,
    melancholic: 30,
    focused: 25,
  },
  recommended_listening_time: '21:00 - 00:00',
  ai_advice: 'Hãy thử cân bằng với một vài bản Acoustic hoặc Lo-fi êm dịu vào cuối tuần để tâm trí được lắng đọng hơn.',
  provider_used: 'groq',
  model_name: 'openai/gpt-oss-120b',
  created_at: new Date().toISOString(),
};

export const MOCK_GENRES: GenreDistributionData = {
  genres: [
    { name: 'EDM / Electronic', plays: 185, percentage: 43.2, color: '#1DB954' },
    { name: 'Global Pop', plays: 120, percentage: 28.0, color: '#06B6D4' },
    { name: 'V-Pop', plays: 68, percentage: 15.9, color: '#EC4899' },
    { name: 'US-UK / Pop', plays: 35, percentage: 8.2, color: '#3B82F6' },
    { name: 'Acoustic / Lo-Fi', plays: 20, percentage: 4.7, color: '#10B981' },
  ],
  total_plays: 428,
  top_genre: 'EDM / Electronic',
};

export const MOCK_LISTENING_HISTORY: ListeningHistoryRecord[] = [
  {
    id: 101,
    played_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    context_type: 'playlist',
    track: {
      spotify_id: 'mock_1',
      name: 'Chúng Ta Của Tương Lai',
      duration_ms: 245000,
      album: {
        spotify_id: 'alb_1',
        name: 'Chúng Ta',
        image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
      },
      artists: [{ spotify_id: 'art_1', name: 'Sơn Tùng M-TP' }],
      danceability: 0.72,
      energy: 0.81,
    },
  },
  {
    id: 102,
    played_at: new Date(Date.now() - 22 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 22 * 60 * 1000).toISOString(),
    context_type: 'album',
    track: {
      spotify_id: 'mock_2',
      name: 'Nấu Ăn Cho Em',
      duration_ms: 220000,
      album: {
        spotify_id: 'alb_2',
        name: 'Nấu Ăn Cho Em',
        image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
      },
      artists: [
        { spotify_id: 'art_2', name: 'Đen Vâu' },
        { spotify_id: 'art_pialinh', name: 'PiaLinh' },
      ],
      danceability: 0.65,
      energy: 0.58,
    },
  },
  {
    id: 103,
    played_at: new Date(Date.now() - 54 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 54 * 60 * 1000).toISOString(),
    context_type: 'playlist',
    track: {
      spotify_id: 'mock_3',
      name: 'Từng Là',
      duration_ms: 215000,
      album: {
        spotify_id: 'alb_3',
        name: 'Từng Là',
        image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
      },
      artists: [{ spotify_id: 'art_4', name: 'Vũ Cát Tường' }],
      danceability: 0.58,
      energy: 0.45,
    },
  },
  {
    id: 104,
    played_at: new Date(Date.now() - 110 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 110 * 60 * 1000).toISOString(),
    context_type: 'user_collection',
    track: {
      spotify_id: 'mock_4',
      name: 'Blinding Lights',
      duration_ms: 200000,
      album: {
        spotify_id: 'alb_4',
        name: 'After Hours',
        image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
      },
      artists: [{ spotify_id: 'art_3', name: 'The Weeknd' }],
      danceability: 0.85,
      energy: 0.89,
    },
  },
  {
    id: 105,
    played_at: new Date(Date.now() - 165 * 60 * 1000).toISOString(),
    created_at: new Date(Date.now() - 165 * 60 * 1000).toISOString(),
    context_type: 'playlist',
    track: {
      spotify_id: 'mock_5',
      name: 'Levitating',
      duration_ms: 203000,
      album: {
        spotify_id: 'alb_5',
        name: 'Future Nostalgia',
        image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
      },
      artists: [{ spotify_id: 'art_5', name: 'Dua Lipa' }],
      danceability: 0.79,
      energy: 0.82,
    },
  },
];

function formatISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getISOWeekDetails(date: Date): { year: number; week: number } {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: d.getUTCFullYear(), week: weekNo };
}

// Sinh danh sach ky thoi gian mau tu dong theo thoi gian thuc
export function getDynamicMockCalendarPeriods(): Record<CalendarPeriodType, CalendarPeriodItem[]> {
  const now = new Date();

  // 1. Tuan (ISO Week)
  const day = (now.getDay() + 6) % 7;
  const currMonday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day);
  const weeks: CalendarPeriodItem[] = [];

  for (let i = 0; i < 3; i++) {
    const mon = new Date(currMonday.getFullYear(), currMonday.getMonth(), currMonday.getDate() - i * 7);
    const sun = new Date(mon.getFullYear(), mon.getMonth(), mon.getDate() + 6);
    const { year: isoY, week: isoW } = getISOWeekDetails(mon);
    const isCurr = i === 0;

    weeks.push({
      key: `${isoY}-W${String(isoW).padStart(2, '0')}`,
      label: isCurr ? 'Tuần này' : `Tuần ${isoW}`,
      start_date: formatISODate(mon),
      end_date: formatISODate(sun),
      is_current: isCurr,
      play_count: i === 0 ? 311 : i === 1 ? 250 : 0,
    });
  }

  // 2. Thang
  const months: CalendarPeriodItem[] = [];
  for (let i = 0; i < 3; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const y = d.getFullYear();
    const m = d.getMonth() + 1;
    const lastDay = new Date(y, m, 0).getDate();
    const isCurr = i === 0;
    const mStr = String(m).padStart(2, '0');

    months.push({
      key: `${y}-${mStr}`,
      label: `Tháng ${mStr}/${y}`,
      start_date: `${y}-${mStr}-01`,
      end_date: `${y}-${mStr}-${String(lastDay).padStart(2, '0')}`,
      is_current: isCurr,
      play_count: i === 0 ? 685 : i === 1 ? 540 : 0,
    });
  }

  // 3. Nam
  const years: CalendarPeriodItem[] = [];
  const currYear = now.getFullYear();
  for (let i = 0; i < 3; i++) {
    const y = currYear - i;
    const isCurr = i === 0;

    years.push({
      key: `${y}`,
      label: `Năm ${y}`,
      start_date: `${y}-01-01`,
      end_date: `${y}-12-31`,
      is_current: isCurr,
      play_count: i === 0 ? 2840 : i === 1 ? 2150 : 0,
    });
  }

  return { week: weeks, month: months, year: years };
}

export const MOCK_CALENDAR_PERIODS: Record<CalendarPeriodType, CalendarPeriodItem[]> = getDynamicMockCalendarPeriods();


export function buildMockRecommendations(trackId: string): RecommendationResult {
  return {
    seed_track: {
      spotify_id: trackId,
      name: 'Bài hát gốc (Demo)',
      artists: ['Nghệ sĩ mẫu'],
      album: 'Album mẫu',
      image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
    },
    recommendations: [
      {
        spotify_id: 'rec_1',
        name: 'Âm Hưởng Tương Đồng 1',
        artists: ['Nghệ sĩ tương đồng'],
        album: 'Album tương đồng',
        image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
        similarity_score: 0.94,
      },
      {
        spotify_id: 'rec_2',
        name: 'Âm Hưởng Tương Đồng 2',
        artists: ['Nghệ sĩ tương đồng'],
        album: 'Album tương đồng',
        image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
        similarity_score: 0.88,
      },
    ],
  };
}

// API Services (khong tra ve du lieu gia khi nguoi dung da dang nhap gap loi)
export const api = {
  // Auth
  async getLoginUrl(): Promise<string> {
    try {
      const res = await apiClient.get('/api/users/spotify/login/');
      return res.data.auth_url;
    } catch (err) {
      throw toApiError(err, 'Không thể khởi tạo đường dẫn đăng nhập Spotify.');
    }
  },

  async exchangeSpotifyCode(exchangeCode: string): Promise<SpotifyExchangeResponse> {
    try {
      const res = await apiClient.post('/api/users/spotify/exchange/', {
        exchange_code: exchangeCode,
      });
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể hoàn tất trao đổi phiên đăng nhập Spotify.');
    }
  },

  async getCurrentUser(): Promise<UserProfile | null> {
    const token = localStorage.getItem('access_token');
    if (!token) {
      return null;
    }
    try {
      const res = await apiClient.get('/api/users/me/');
      return res.data.user || res.data;
    } catch (err) {
      const apiErr = toApiError(err, 'Không thể xác minh phiên đăng nhập.');
      if (apiErr.status === 401 || apiErr.status === 403) {
        localStorage.removeItem('access_token');
        return null;
      }
      throw apiErr;
    }
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/api/users/logout/');
    } finally {
      localStorage.removeItem('access_token');
    }
  },

  // Tracker
  async triggerSync(): Promise<{ scrobbled_count: number; message?: string }> {
    try {
      const res = await apiClient.post('/api/tracker/sync/');
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể đồng bộ dữ liệu từ Spotify.');
    }
  },

  async getListeningHistory(limit: number = 20, signal?: AbortSignal): Promise<ListeningHistoryRecord[]> {
    try {
      const res = await apiClient.get(`/api/tracker/history/?limit=${limit}`, { signal });
      if (Array.isArray(res.data)) {
        return res.data;
      }
      if (res.data && Array.isArray(res.data.results)) {
        return res.data.results;
      }
      return [];
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải nhật ký nghe nhạc gần đây.');
    }
  },

  // Analytics Calendar Periods
  async getAvailablePeriods(
    periodType: CalendarPeriodType = 'week',
    limit: number = 12,
    signal?: AbortSignal
  ): Promise<CalendarPeriodItem[]> {
    try {
      const res = await apiClient.get(`/api/analytics/periods/?period_type=${periodType}&limit=${limit}`, { signal });
      if (res.data && Array.isArray(res.data.periods)) {
        return res.data.periods;
      }
      return [];
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải danh sách kỳ thống kê.');
    }
  },

  // Analytics
  async getSummary(filter?: TimeFilterInput, signal?: AbortSignal): Promise<SummaryStats> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/summary/?${params}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải số liệu tổng quan.');
    }
  },

  async getTopTracks(filter?: TimeFilterInput, limit: number = 5, signal?: AbortSignal): Promise<TopTrack[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-tracks/?${params}&limit=${limit}`, { signal });
      return Array.isArray(res.data?.tracks) ? res.data.tracks : [];
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải danh sách Top bài hát.');
    }
  },

  async getTopArtists(filter?: TimeFilterInput, limit: number = 5, signal?: AbortSignal): Promise<TopArtist[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-artists/?${params}&limit=${limit}`, { signal });
      return Array.isArray(res.data?.artists) ? res.data.artists : [];
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải danh sách Top nghệ sĩ.');
    }
  },

  async getTopAlbums(filter?: TimeFilterInput, limit: number = 5, signal?: AbortSignal): Promise<TopAlbum[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-albums/?${params}&limit=${limit}`, { signal });
      return Array.isArray(res.data?.albums) ? res.data.albums : [];
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải danh sách Top album.');
    }
  },

  async getRadar(filter?: TimeFilterInput, signal?: AbortSignal): Promise<RadarData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/radar/?${params}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải biểu đồ đặc trưng âm thanh.');
    }
  },

  async getHeatmap(filter?: TimeFilterInput, periodType?: string, signal?: AbortSignal): Promise<HeatmapData> {
    const params = buildTimeParams(filter);
    const fullParams = periodType ? `${params}&period_type=${periodType}` : params;
    try {
      const res = await apiClient.get(`/api/analytics/heatmap/?${fullParams}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải bản đồ nhiệt nghe nhạc.');
    }
  },

  async getWeeklyComparison(
    filter?: TimeFilterInput,
    periodType?: CalendarPeriodType,
    signal?: AbortSignal
  ): Promise<WeeklyComparisonData> {
    const params = buildTimeParams(filter);
    const fullParams = periodType ? `${params}&period_type=${periodType}` : params;
    try {
      const res = await apiClient.get(`/api/analytics/weekly-comparison/?${fullParams}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải dữ liệu so sánh xu hướng.');
    }
  },

  async getGenreDistribution(filter?: TimeFilterInput, signal?: AbortSignal): Promise<GenreDistributionData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/genres/?${params}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải phân bố thể loại âm nhạc.');
    }
  },

  // AI Insights
  async getLatestPersona(period: string = 'monthly', signal?: AbortSignal): Promise<AIMusicPersona | null> {
    try {
      const res = await apiClient.get(`/api/ai/persona/latest/?period_type=${period}`, { signal });
      const data = res.data;
      if (!data || typeof data !== 'object' || !data.persona_title || !data.mood_distribution) {
        return null;
      }
      return data as AIMusicPersona;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải hồ sơ AI Music Persona.');
    }
  },

  async generatePersona(period: string = 'monthly'): Promise<AIMusicPersona> {
    try {
      const res = await apiClient.post('/api/ai/persona/generate/', { period_type: period });
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể tạo phân tích AI Music Persona.');
    }
  },

  async getRecommendations(trackId: string, topK: number = 5): Promise<RecommendationResult> {
    try {
      const res = await apiClient.get(`/api/ai/recommendations/?track_id=${trackId}&top_k=${topK}`);
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể tìm các bài hát tương đồng.');
    }
  },

  async getMusicFacts(
    period: string = 'week',
    forceRefresh: boolean = false,
    trigger: boolean = false,
    signal?: AbortSignal
  ): Promise<MusicFactsResponse> {
    try {
      const refreshParam = forceRefresh ? '&refresh=true' : '';
      const triggerParam = trigger ? '&trigger=true' : '';
      const res = await apiClient.get(`/api/ai/facts/?period=${period}${refreshParam}${triggerParam}`, { signal });
      return res.data;
    } catch (err) {
      if (isRequestCanceled(err)) throw err;
      throw toApiError(err, 'Không thể tải phân tích từ AI Music Detective.');
    }
  },

  // Codebase RAG
  async queryCodebase(payload: CodebaseQueryPayload): Promise<CodebaseQueryResponse> {
    try {
      const res = await apiClient.post('/api/ai/codebase/query/', payload);
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể kết nối đến hệ thống trợ lý RAG.');
    }
  },

  async reindexCodebase(): Promise<{ status: string; chunks_count: number; duration_s: number }> {
    try {
      const res = await apiClient.post('/api/ai/codebase/index/');
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể lập chỉ mục lại hệ thống.');
    }
  },

  // Unified Hybrid Music & Website Assistant
  async queryAssistant(payload: AssistantQueryPayload): Promise<AssistantQueryResponse> {
    try {
      const res = await apiClient.post('/api/ai/assistant/query/', payload);
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể kết nối đến MusicTrack Assistant.');
    }
  },

  async clearAssistantSession(sessionId: string = 'default'): Promise<{ status: string; session_id: string }> {
    try {
      const res = await apiClient.post('/api/ai/assistant/session/clear/', { session_id: sessionId });
      return res.data;
    } catch (err) {
      throw toApiError(err, 'Không thể xóa lịch sử hội thoại trên máy chủ.');
    }
  },
};

export const MOCK_MUSIC_FACTS: MusicFactsResponse = {
  facts: [
    {
      id: 'fact-1',
      category: 'repeat_loop',
      badge: 'Vòng Lặp Vô Tận',
      title: 'Cơn Nghiện Astral Projection',
      description: 'Bạn đã bấm nghe liên tiếp bản nhạc này 7 lần chỉ trong một ngày mà không hề chuyển bài.',
      metric_highlight: '7 lần / ngày',
      evidence: 'Hallmore - Astral Projection (Thứ Tư)',
    },
    {
      id: 'fact-2',
      category: 'artist_dominance',
      badge: 'Độ Trung Thành Tuyệt Đối',
      title: 'Vùng An Toàn Cùng Alan Walker',
      description: 'Alan Walker chiếm tới 46.8% toàn bộ thời lượng nghe nhạc của bạn trong suốt kỳ này.',
      metric_highlight: '46.8% thời lượng',
      evidence: '58 lượt nghe trên tổng số 124 lượt',
    },
    {
      id: 'fact-3',
      category: 'marathon',
      badge: 'Kỷ Lục Marathon',
      title: 'Phiên Nghe Bất Tận Chiều Cuối Tuần',
      description: 'Bạn đã đắm chìm trong âm nhạc suốt 3.8 giờ liên tục với 45 bài hát không hề gián đoạn.',
      metric_highlight: '3.8 giờ liên tục',
      evidence: '14:30 - 18:18 Ngày Chủ Nhật',
    },
  ],
  agent_meta: {
    agent_name: 'Aura Music Detective',
    provider_used: 'groq',
    model_name: 'openai/gpt-oss-120b',
    iterations_used: 2,
    tools_called: ['query_repeat_loops', 'query_artist_dominance'],
    is_fallback: false,
  },
  period_key: 'week',
  period_label: 'Tuần này',
};

