export type TimeRange = '7d' | '30d' | '1y';

export interface SummaryStats {
  total_plays: number;
  total_duration_ms: number;
  total_hours: number;
  unique_artists_count: number;
  unique_albums_count: number;
  time_range: string;
}

export interface TopTrack {
  spotify_id: string;
  name: string;
  album_name: string;
  album_image_url: string;
  artists: string[];
  play_count: number;
}

export interface TopArtist {
  spotify_id: string;
  name: string;
  image_url: string | null;
  play_count: number;
}

export interface AudioFeatureItem {
  attribute: string;
  score: number;
  description?: string;
}

export interface RadarData {
  time_range: string;
  total_tracks_analyzed: number;
  features: AudioFeatureItem[];
}

export interface HeatmapCell {
  day_of_week: number;
  day_name?: string;
  hour: number;
  count: number;
}

export interface HeatmapData {
  time_range: string;
  max_density: number;
  matrix: HeatmapCell[];
}

export interface RankingEntry {
  name: string;
  plays: number;
  cumulative_plays: number;
}

export interface TimelineFrame {
  date: string;
  rankings: RankingEntry[];
}

export interface BarChartRaceData {
  metric: string;
  timeline: TimelineFrame[];
}

export interface GenreItem {
  name: string;
  plays: number;
  percentage: number;
  color: string;
}

export interface GenreDistributionData {
  genres: GenreItem[];
  total_plays: number;
  top_genre: string;
}

export interface HistoryTrackArtist {
  spotify_id: string;
  name: string;
  genres?: string[];
  image_url?: string | null;
}

export interface HistoryTrackAlbum {
  spotify_id: string;
  name: string;
  release_date?: string;
  image_url?: string | null;
}

export interface HistoryTrack {
  spotify_id: string;
  name: string;
  duration_ms: number;
  album?: HistoryTrackAlbum | null;
  artists: HistoryTrackArtist[];
  danceability?: number;
  energy?: number;
  valence?: number;
  acousticness?: number;
  tempo?: number;
  features_synced?: boolean;
}

export interface ListeningHistoryRecord {
  id: number;
  track: HistoryTrack;
  played_at: string;
  context_type?: string | null;
  created_at: string;
}

export type CalendarPeriodType = 'week' | 'month' | 'year';

export interface CalendarPeriodItem {
  key: string;
  label: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  play_count: number;
}

export interface CalendarPeriodsResponse {
  period_type: CalendarPeriodType;
  periods: CalendarPeriodItem[];
}


