export interface UserProfile {
  id: number;
  username: string;
  email: string;
  display_name: string;
  profile_image_url: string | null;
  is_spotify_connected: boolean;
  is_sync_active: boolean;
  last_synced_at: string | null;
}

export interface SpotifyAuthResponse {
  access_token: string;
  user: UserProfile;
}
