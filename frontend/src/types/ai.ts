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

export function isValidPersona(persona?: AIMusicPersona | null): persona is AIMusicPersona {
  return Boolean(
    persona &&
      typeof persona === 'object' &&
      typeof persona.persona_title === 'string' &&
      persona.persona_title.trim().length > 0 &&
      persona.mood_distribution &&
      typeof persona.mood_distribution === 'object'
  );
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

export interface MusicFact {
  id: string;
  category: 'repeat_loop' | 'night_owl' | 'marathon' | 'artist_dominance' | 'contrast' | 'milestone' | 'general';
  badge: string;
  title: string;
  description: string;
  metric_highlight: string;
  evidence?: string;
}

export interface AgentMeta {
  agent_name: string;
  provider_used: string;
  model_name: string;
  iterations_used: number;
  tools_called: string[];
  is_fallback: boolean;
}

export interface MusicFactsResponse {
  facts: MusicFact[];
  agent_meta: AgentMeta;
  period_key: string;
  period_label: string;
}

export interface CitationItem {
  citation_id: string;
  file_path: string;
  line_start: number;
  line_end: number;
  symbol?: string | null;
  snippet: string;
}

export interface CodebaseQueryResponse {
  query: string;
  answer: string;
  citations: CitationItem[];
  verification: {
    is_escape_hatch?: boolean;
    total_citations: number;
    valid_context_citations: number;
    valid_file_citations: number;
    citation_existence_rate: number;
    citation_accuracy: number;
    all_valid: boolean;
  };
  latency_ms: number;
  retrieved_chunks_count: number;
}

export interface CodebaseQueryPayload {
  query: string;
  mode?: 'baseline_dense' | 'hybrid_rrf' | 'full_cascade';
  top_k?: number;
  use_cache?: boolean;
}

export type AssistantMode = 'auto' | 'music_insights' | 'website_support';
export type AssistantResolvedDomain = 'music_insights' | 'website_support' | 'clarification';
export type AssistantRagMode = 'baseline_dense' | 'hybrid_rrf' | 'full_cascade';

export interface AssistantPeriodContext {
  period_type?: 'week' | 'month' | 'year';
  start_date?: string;
  end_date?: string;
  label?: string;
}

export interface AssistantScopeMeta {
  label: string;
  start_date?: string | null;
  end_date?: string | null;
  source: 'dashboard_period' | 'requested_in_query' | 'rolling_window' | 'website_docs' | 'clarification';
  note?: string;
}

export interface AssistantEvidenceItem {
  label: string;
  value: string;
  detail?: string;
  is_estimate: boolean;
  category: 'observed' | 'calculated' | 'estimate' | 'ai_interpretation';
}

export interface AssistantTopicItem {
  id: string;
  title: string;
  category: string;
}

export interface AssistantClarificationOption {
  mode: 'music_insights' | 'website_support';
  label: string;
  query: string;
}

export interface AssistantResponseMeta {
  provider_used: string;
  model_name: string;
  is_fallback: boolean;
  tools_used: string[];
  session_turns: number;
  has_compressed_memory?: boolean;
  memory_policy: string;
}

export interface AssistantQueryPayload {
  query: string;
  mode?: AssistantMode;
  session_id?: string;
  period_context?: AssistantPeriodContext | null;
  rag_mode?: AssistantRagMode;
  top_k?: number;
  use_cache?: boolean;
}

export interface AssistantQueryResponse {
  query: string;
  answer: string;
  active_mode: AssistantMode;
  resolved_domain: AssistantResolvedDomain;
  needs_clarification: boolean;
  clarification_options: AssistantClarificationOption[];
  suggested_scopes?: AssistantClarificationOption[];
  scope: AssistantScopeMeta;
  evidence: AssistantEvidenceItem[];
  topics: AssistantTopicItem[];
  dev_citations?: CitationItem[];
  dev_verification?: CodebaseQueryResponse['verification'] | null;
  dev_metrics?: {
    latency_ms: number;
    retrieved_chunks_count: number;
    rag_mode: string;
  } | null;
  meta: AssistantResponseMeta;
}

export interface AssistantConversationTurn {
  id: string;
  query: string;
  response: AssistantQueryResponse;
  createdAt: string;
}


