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

export interface TopAlbum {
  spotify_id: string;
  name: string;
  image_url: string | null;
  release_date?: string;
  artists: string[];
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

export interface MonthHeatmapDay {
  date: string;
  day_number: number;
  day_of_week: number;
  count: number;
  is_current_month: boolean;
}

export interface MonthHeatmapData {
  year: number;
  month: number;
  first_day_weekday: number;
  total_days: number;
  total_plays: number;
  peak_day: string;
  peak_plays: number;
  active_days: number;
  max_density: number;
  days: MonthHeatmapDay[];
}

export interface YearHeatmapDay {
  date: string;
  month: number;
  day_number: number;
  day_of_week: number;
  week_index: number;
  count: number;
  is_in_range: boolean;
}

export interface YearMonthHeader {
  month: number;
  label: string;
  start_week: number;
}

export interface YearHeatmapData {
  year: number;
  total_weeks: number;
  total_days: number;
  total_plays: number;
  peak_day: string;
  peak_plays: number;
  active_days: number;
  longest_streak: number;
  top_month: number;
  top_month_plays: number;
  max_density: number;
  months_header: YearMonthHeader[];
  days: YearHeatmapDay[];
}

export interface HeatmapData {
  time_range: string;
  period_type?: 'week' | 'month' | 'year';
  max_density: number;
  matrix: HeatmapCell[];
  month_calendar?: MonthHeatmapData;
  year_calendar?: YearHeatmapData;
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

export interface DayComparison {
  day_index: number;
  day_name: string;
  day_name_en: string;
  current_week_plays: number;
  previous_week_plays: number;
  diff: number;
}

export interface WeeklyComparisonSummary {
  total_current_week: number;
  total_previous_week: number;
  growth_percentage: number;
  peak_day_current: string;
  peak_plays_current: number;
}

export interface WeeklyComparisonData {
  time_range: string;
  current_week_label: string;
  previous_week_label: string;
  days: DayComparison[];
  summary: WeeklyComparisonSummary;
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


