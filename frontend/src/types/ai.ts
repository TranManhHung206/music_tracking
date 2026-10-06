export interface AIMusicPersona {
  id?: number;
  period_type: 'weekly' | 'monthly' | 'all_time';
  persona_title: string;
  tagline: string;
  vibe_summary: string;
  mood_distribution: Record<string, number>;
  recommended_listening_time?: string;
  ai_advice: string;
  provider_used?: string;
  model_name?: string;
  created_at?: string;
}

export interface SongRecommendation {
  spotify_id: string;
  name: string;
  artists: string[];
  album: string;
  image_url: string;
  similarity_score: number;
}

export interface SeedTrackInfo {
  spotify_id: string;
  name: string;
  artists: string[];
  album: string;
  image_url: string;
  audio_features?: {
    danceability: number;
    energy: number;
    valence: number;
    acousticness: number;
    tempo: number;
  };
}

export interface RecommendationResult {
  seed_track: SeedTrackInfo;
  recommendations: SongRecommendation[];
}
