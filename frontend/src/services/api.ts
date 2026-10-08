import axios from 'axios';
import type { UserProfile } from '../types/auth';
import type {
  TimeRange,
  SummaryStats,
  TopTrack,
  TopArtist,
  RadarData,
  HeatmapData,
  BarChartRaceData,
  GenreDistributionData,
} from '../types/analytics';
import type { AIMusicPersona, RecommendationResult } from '../types/ai';

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

  // Analytics
  async getSummary(range: TimeRange = '30d'): Promise<SummaryStats> {
    try {
      const res = await apiClient.get(`/api/analytics/summary/?time_range=${range}`);
      return res.data;
    } catch {
      return { ...MOCK_SUMMARY, time_range: range };
    }
  },

  async getTopTracks(range: TimeRange = '30d', limit: number = 5): Promise<TopTrack[]> {
    try {
      const res = await apiClient.get(`/api/analytics/top-tracks/?time_range=${range}&limit=${limit}`);
      return res.data.tracks || res.data;
    } catch {
      return MOCK_TOP_TRACKS.slice(0, limit);
    }
  },

  async getTopArtists(range: TimeRange = '30d', limit: number = 5): Promise<TopArtist[]> {
    try {
      const res = await apiClient.get(`/api/analytics/top-artists/?time_range=${range}&limit=${limit}`);
      return res.data.artists || res.data;
    } catch {
      return MOCK_TOP_ARTISTS.slice(0, limit);
    }
  },

  async getRadar(range: TimeRange = '30d'): Promise<RadarData> {
    try {
      const res = await apiClient.get(`/api/analytics/radar/?time_range=${range}`);
      return res.data;
    } catch {
      return { ...MOCK_RADAR, time_range: range };
    }
  },

  async getHeatmap(range: TimeRange = '30d'): Promise<HeatmapData> {
    try {
      const res = await apiClient.get(`/api/analytics/heatmap/?time_range=${range}`);
      return res.data;
    } catch {
      return { ...MOCK_HEATMAP, time_range: range };
    }
  },

  async getBarChartRace(range: TimeRange = '1y'): Promise<BarChartRaceData> {
    try {
      const res = await apiClient.get(`/api/analytics/bar-chart-race/?time_range=${range}`);
      return res.data;
    } catch {
      return MOCK_RACE;
    }
  },

  async getGenreDistribution(range: TimeRange = '30d'): Promise<GenreDistributionData> {
    try {
      const res = await apiClient.get(`/api/analytics/genres/?time_range=${range}`);
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
};
