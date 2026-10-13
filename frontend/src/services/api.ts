import axios from 'axios';
import type { UserProfile } from '../types/auth';
import type {
  TimeRange,
  SummaryStats,
  TopTrack,
  TopArtist,
  TopAlbum,
  RadarData,
  HeatmapData,
  BarChartRaceData,
  WeeklyComparisonData,
  GenreDistributionData,
  ListeningHistoryRecord,
  CalendarPeriodType,
  CalendarPeriodItem,
} from '../types/analytics';
import type { AIMusicPersona, RecommendationResult, MusicFactsResponse } from '../types/ai';

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
  return config;
});

// Mock Fallback Data de hien thi UI ngay ca khi offline
export const MOCK_USER: UserProfile = {
  id: 1,
  username: 'hungtran_music',
  email: 'hungtran@example.com',
  display_name: 'Hùng Trần',
  profile_image_url: null,
  is_spotify_connected: true,
  is_sync_active: true,
  last_synced_at: new Date().toISOString(),
};

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
    { attribute: 'Valence', score: 0.65, description: 'Tích cực, vui tươi' },
    { attribute: 'Energy', score: 0.78, description: 'Sôi động, mạnh mẽ' },
    { attribute: 'Danceability', score: 0.72, description: 'Dễ nhảy, nhịp điệu rõ' },
    { attribute: 'Acousticness', score: 0.35, description: 'Mộc mạc, ít điện tử' },
    { attribute: 'Tempo', score: 0.62, description: 'Tốc độ nhịp BPM chuẩn hóa' },
  ],
};

export const MOCK_HEATMAP: HeatmapData = {
  time_range: '30d',
  max_density: 18,
  matrix: Array.from({ length: 7 * 24 }, (_, i) => {
    const day = Math.floor(i / 24) + 1;
    const hour = i % 24;
    let count = 0;
    if (hour >= 20 && hour <= 23) {
      count = Math.floor(Math.random() * 15) + 4;
    } else if (hour >= 8 && hour <= 18) {
      count = Math.floor(Math.random() * 8);
    } else if (hour >= 0 && hour <= 2) {
      count = Math.floor(Math.random() * 10) + 2;
    }
    return { day_of_week: day, hour, count };
  }),
};

export const MOCK_RACE: BarChartRaceData = {
  metric: 'artists',
  timeline: [
    {
      date: '2026-05',
      rankings: [
        { name: 'Sơn Tùng M-TP', plays: 25, cumulative_plays: 25 },
        { name: 'Đen Vâu', plays: 18, cumulative_plays: 18 },
        { name: 'The Weeknd', plays: 15, cumulative_plays: 15 },
        { name: 'Vũ Cát Tường', plays: 10, cumulative_plays: 10 },
        { name: 'Dua Lipa', plays: 8, cumulative_plays: 8 },
      ],
    },
    {
      date: '2026-06',
      rankings: [
        { name: 'Sơn Tùng M-TP', plays: 22, cumulative_plays: 47 },
        { name: 'Đen Vâu', plays: 24, cumulative_plays: 42 },
        { name: 'The Weeknd', plays: 18, cumulative_plays: 33 },
        { name: 'Vũ Cát Tường', plays: 14, cumulative_plays: 24 },
        { name: 'Dua Lipa', plays: 12, cumulative_plays: 20 },
      ],
    },
    {
      date: '2026-07',
      rankings: [
        { name: 'Sơn Tùng M-TP', plays: 30, cumulative_plays: 77 },
        { name: 'Đen Vâu', plays: 20, cumulative_plays: 62 },
        { name: 'The Weeknd', plays: 22, cumulative_plays: 55 },
        { name: 'Dua Lipa', plays: 20, cumulative_plays: 40 },
        { name: 'Vũ Cát Tường', plays: 12, cumulative_plays: 36 },
      ],
    },
    {
      date: '2026-08',
      rankings: [
        { name: 'Sơn Tùng M-TP', plays: 25, cumulative_plays: 102 },
        { name: 'The Weeknd', plays: 28, cumulative_plays: 83 },
        { name: 'Đen Vâu', plays: 15, cumulative_plays: 77 },
        { name: 'Dua Lipa', plays: 25, cumulative_plays: 65 },
        { name: 'Vũ Cát Tường', plays: 14, cumulative_plays: 50 },
      ],
    },
  ],
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
    total_current_week: 311,
    total_previous_week: 250,
    growth_percentage: 24.4,
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
    { name: 'Acoustic / Lo-Fi', plays: 20, percentage: 4.7, color: '#A855F7' },
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
      play_count: isCurr ? 222 : 0,
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
      play_count: isCurr ? 222 : 0,
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
      play_count: isCurr ? 222 : 0,
    });
  }

  return { week: weeks, month: months, year: years };
}

export const MOCK_CALENDAR_PERIODS: Record<CalendarPeriodType, CalendarPeriodItem[]> = getDynamicMockCalendarPeriods();


// API Services voi Graceful Fallback sang Mock Data
export const api = {
  // Auth
  async getLoginUrl(): Promise<string> {
    try {
      const res = await apiClient.get('/api/users/spotify/login/');
      return res.data.auth_url;
    } catch {
      return '#';
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
    } catch {
      localStorage.removeItem('access_token');
      return null;
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
    const res = await apiClient.post('/api/tracker/sync/');
    return res.data;
  },

  async getListeningHistory(limit: number = 20): Promise<ListeningHistoryRecord[]> {
    try {
      const res = await apiClient.get(`/api/tracker/history/?limit=${limit}`);
      if (Array.isArray(res.data)) {
        return res.data;
      }
      if (res.data && Array.isArray(res.data.results)) {
        return res.data.results;
      }
      return MOCK_LISTENING_HISTORY.slice(0, limit);
    } catch {
      return MOCK_LISTENING_HISTORY.slice(0, limit);
    }
  },

  // Analytics Calendar Periods
  async getAvailablePeriods(periodType: CalendarPeriodType = 'week', limit: number = 12): Promise<CalendarPeriodItem[]> {
    try {
      const res = await apiClient.get(`/api/analytics/periods/?period_type=${periodType}&limit=${limit}`);
      if (res.data && Array.isArray(res.data.periods)) {
        return res.data.periods;
      }
      return MOCK_CALENDAR_PERIODS[periodType] || [];
    } catch {
      return MOCK_CALENDAR_PERIODS[periodType] || [];
    }
  },

  // Analytics
  async getSummary(filter?: TimeFilterInput): Promise<SummaryStats> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/summary/?${params}`);
      return res.data;
    } catch {
      const rangeStr = typeof filter === 'string' ? filter : (filter?.time_range || '30d');
      return { ...MOCK_SUMMARY, time_range: rangeStr };
    }
  },

  async getTopTracks(filter?: TimeFilterInput, limit: number = 5): Promise<TopTrack[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-tracks/?${params}&limit=${limit}`);
      return res.data.tracks || res.data;
    } catch {
      return MOCK_TOP_TRACKS.slice(0, limit);
    }
  },

  async getTopArtists(filter?: TimeFilterInput, limit: number = 5): Promise<TopArtist[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-artists/?${params}&limit=${limit}`);
      return res.data.artists || res.data;
    } catch {
      return MOCK_TOP_ARTISTS.slice(0, limit);
    }
  },

  async getTopAlbums(filter?: TimeFilterInput, limit: number = 5): Promise<TopAlbum[]> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/top-albums/?${params}&limit=${limit}`);
      return res.data.albums || res.data;
    } catch {
      return MOCK_TOP_ALBUMS.slice(0, limit);
    }
  },

  async getRadar(filter?: TimeFilterInput): Promise<RadarData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/radar/?${params}`);
      return res.data;
    } catch {
      const rangeStr = typeof filter === 'string' ? filter : (filter?.time_range || '30d');
      return { ...MOCK_RADAR, time_range: rangeStr };
    }
  },

  async getHeatmap(filter?: TimeFilterInput): Promise<HeatmapData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/heatmap/?${params}`);
      return res.data;
    } catch {
      const rangeStr = typeof filter === 'string' ? filter : (filter?.time_range || '30d');
      return { ...MOCK_HEATMAP, time_range: rangeStr };
    }
  },

  async getBarChartRace(filter?: TimeFilterInput): Promise<BarChartRaceData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/bar-chart-race/?${params}`);
      return res.data;
    } catch {
      return MOCK_RACE;
    }
  },

  async getWeeklyComparison(filter?: TimeFilterInput): Promise<WeeklyComparisonData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/weekly-comparison/?${params}`);
      return res.data;
    } catch {
      return MOCK_WEEKLY_COMPARISON;
    }
  },

  async getGenreDistribution(filter?: TimeFilterInput): Promise<GenreDistributionData> {
    const params = buildTimeParams(filter);
    try {
      const res = await apiClient.get(`/api/analytics/genres/?${params}`);
      return res.data;
    } catch {
      return MOCK_GENRES;
    }
  },

  // AI Insights
  async getLatestPersona(period: string = 'monthly'): Promise<AIMusicPersona> {
    try {
      const res = await apiClient.get(`/api/ai/persona/latest/?period_type=${period}`);
      return res.data;
    } catch {
      return MOCK_PERSONA;
    }
  },

  async generatePersona(period: string = 'monthly'): Promise<AIMusicPersona> {
    try {
      const res = await apiClient.post('/api/ai/persona/generate/', { period_type: period });
      return res.data;
    } catch {
      return MOCK_PERSONA;
    }
  },

  async getRecommendations(trackId: string, topK: number = 5): Promise<RecommendationResult> {
    try {
      const res = await apiClient.get(`/api/ai/recommendations/?track_id=${trackId}&top_k=${topK}`);
      return res.data;
    } catch {
      return {
        seed_track: {
          spotify_id: trackId,
          name: 'Bài hát gốc',
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
  },

  async getMusicFacts(period: string = 'week', forceRefresh: boolean = false): Promise<MusicFactsResponse> {
    try {
      const refreshParam = forceRefresh ? '&refresh=true' : '';
      const res = await apiClient.get(`/api/ai/facts/?period=${period}${refreshParam}`);
      return res.data;
    } catch {
      return MOCK_MUSIC_FACTS;
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

