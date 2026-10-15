from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from rest_framework.test import APIClient
from rest_framework import status

from users.models import SpotifyProfile
from tracker.models import Artist, Album, Track, ListeningHistory
from tracker.services.ingestion import (
    parse_iso_datetime,
    ingest_recently_played_payload,
    sync_audio_features_for_unsynced_tracks,
    sync_artist_images_from_spotify,
)
from tracker.tasks import scheduled_scrobble_all_users

SAMPLE_SPOTIFY_PAYLOAD = {
    "items": [
        {
            "track": {
                "id": "track_001",
                "name": "Knights of Cydonia",
                "duration_ms": 366093,
                "album": {
                    "id": "album_001",
                    "name": "Black Holes and Revelations",
                    "release_date": "2006-07-03",
                    "images": [{"url": "https://example.com/muse.jpg"}]
                },
                "artists": [{"id": "artist_001", "name": "Muse"}]
            },
            "played_at": "2026-10-06T08:15:20.100Z",
            "context": {"type": "album"}
        },
        {
            "track": {
                "id": "track_002",
                "name": "Starboy",
                "duration_ms": 230453,
                "album": {
                    "id": "album_002",
                    "name": "Starboy",
                    "release_date": "2016-11-25",
                    "images": [{"url": "https://example.com/starboy.jpg"}]
                },
                "artists": [{"id": "artist_002", "name": "The Weeknd"}]
            },
            "played_at": "2026-10-06T08:08:10.500Z",
            "context": {"type": "playlist"}
        }
    ]
}

class IngestionServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_user_ingest")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="spotify_user_ingest",
            display_name="Ingest User",
            is_sync_active=True
        )

    def test_parse_iso_datetime(self):
        dt = parse_iso_datetime("2026-10-06T08:15:20.100Z")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 6)

    def test_cursor_calculation(self):
        dt = parse_iso_datetime("2026-10-06T08:15:20.100Z")
        cursor_ms = int(dt.timestamp() * 1000)
        self.assertGreater(cursor_ms, 0)
        self.assertIsInstance(cursor_ms, int)

    def test_ingest_payload_creates_entities(self):
        result = ingest_recently_played_payload(self.user, SAMPLE_SPOTIFY_PAYLOAD)
        self.assertEqual(result["scrobbled_count"], 2)

        # Check DB entities
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(Album.objects.count(), 2)
        self.assertEqual(Track.objects.count(), 2)
        self.assertEqual(ListeningHistory.objects.count(), 2)

        track_1 = Track.objects.get(spotify_id="track_001")
        self.assertEqual(track_1.name, "Knights of Cydonia")
        self.assertEqual(track_1.album.name, "Black Holes and Revelations")
        self.assertEqual(track_1.artists.first().name, "Muse")

    def test_deduplication_two_tier(self):
        # First ingest
        ingest_recently_played_payload(self.user, SAMPLE_SPOTIFY_PAYLOAD)
        self.assertEqual(ListeningHistory.objects.count(), 2)

        # Second ingest with identical payload (should skip duplicates)
        result_2 = ingest_recently_played_payload(self.user, SAMPLE_SPOTIFY_PAYLOAD)
        # Database count remains 2
        self.assertEqual(ListeningHistory.objects.count(), 2)
        self.assertEqual(result_2["scrobbled_count"], 2)

    def test_database_unique_constraint_enforcement(self):
        track = Track.objects.create(spotify_id="trk_unique", name="Unique Track")
        played_at = datetime(2026, 10, 6, 12, 0, 0, tzinfo=dt_timezone.utc)

        ListeningHistory.objects.create(user=self.user, track=track, played_at=played_at)
        with self.assertRaises(IntegrityError):
            ListeningHistory.objects.create(user=self.user, track=track, played_at=played_at)

    def test_audio_features_sync(self):
        track = Track.objects.create(spotify_id="trk_audio", name="Audio Track", features_synced=False)
        mock_features = [
            {
                "id": "trk_audio",
                "danceability": 0.75,
                "energy": 0.82,
                "valence": 0.65,
                "acousticness": 0.12,
                "tempo": 128.5
            }
        ]
        with patch('tracker.services.ingestion.fetch_audio_features_from_api', return_value=mock_features):
            count = sync_audio_features_for_unsynced_tracks(access_token="fake_token")
            self.assertEqual(count, 1)

            track.refresh_from_db()
            self.assertTrue(track.features_synced)
            self.assertEqual(track.danceability, 0.75)
            self.assertEqual(track.tempo, 128.5)

    def test_sync_artist_images_from_spotify(self):
        artist = Artist.objects.create(spotify_id="art_sync_1", name="Artist Sync Test", image_url=None)
        mock_artist_data = {
            "id": "art_sync_1",
            "name": "Artist Sync Test",
            "images": [{"url": "https://i.scdn.co/image/test_art_sync_img"}],
            "genres": ["indie pop", "v-pop"]
        }
        with patch('tracker.services.ingestion.get_valid_access_token', return_value="mock_token"), \
             patch('tracker.services.ingestion.fetch_artist_from_spotify_api', return_value=mock_artist_data):
            res = sync_artist_images_from_spotify(user=self.user, force=True)
            self.assertEqual(res["updated_count"], 1)
            artist.refresh_from_db()
            self.assertEqual(artist.image_url, "https://i.scdn.co/image/test_art_sync_img")
            self.assertEqual(artist.genres, ["indie pop", "v-pop"])

class CeleryTasksTest(TestCase):
    def setUp(self):
        self.user_active = User.objects.create_user(username="u_active")
        SpotifyProfile.objects.create(user=self.user_active, spotify_id="sp_active", is_sync_active=True)

        self.user_inactive = User.objects.create_user(username="u_inactive")
        SpotifyProfile.objects.create(user=self.user_inactive, spotify_id="sp_inactive", is_sync_active=False)

    @patch('tracker.tasks.sync_user_recently_played_task.delay')
    def test_scheduled_scrobble_dispatches_active_users_only(self, mock_delay):
        res = scheduled_scrobble_all_users()
        self.assertEqual(res["dispatched_users_count"], 1)
        mock_delay.assert_called_once_with(self.user_active.id)

class TrackerAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="api_tracker_user")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="sp_tracker_api",
            display_name="Tracker API User",
            is_sync_active=True
        )
        self.client.force_authenticate(user=self.user)

        # Create sample history
        self.track = Track.objects.create(spotify_id="api_trk_1", name="API Test Track", duration_ms=200000)
        self.history = ListeningHistory.objects.create(
            user=self.user,
            track=self.track,
            played_at=datetime(2026, 10, 6, 10, 0, 0, tzinfo=dt_timezone.utc)
        )

    def test_get_history_endpoint(self):
        response = self.client.get('/api/tracker/history/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["track"]["name"], "API Test Track")

    def test_get_status_endpoint(self):
        response = self.client.get('/api/tracker/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["is_sync_active"])
        self.assertEqual(data["total_scrobbles"], 1)

class AutoSyncCommandTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="auto_sync_test_user")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="sp_auto_sync_1",
            display_name="Auto Sync User",
            is_sync_active=True
        )

    @patch('tracker.management.commands.run_auto_sync.sync_user_recently_played_pipeline')
    def test_run_auto_sync_once(self, mock_sync):
        from django.core.management import call_command
        from io import StringIO

        mock_sync.return_value = {
            "status": "success",
            "scrobbled_count": 5,
            "features_synced_count": 5,
            "sync_mode": "latest_50"
        }

        out = StringIO()
        call_command('run_auto_sync', '--once', '--interval', '1', stdout=out)
        output_str = out.getvalue()

        self.assertIn("Khoi dong Auto-Sync Daemon", output_str)
        self.assertIn("auto_sync_test_user", output_str)
        self.assertIn("new_tracks=5", output_str)
        self.assertIn("Da dung Auto-Sync Daemon an toan.", output_str)
        mock_sync.assert_called_once_with(self.user)

