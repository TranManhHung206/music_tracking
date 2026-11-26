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
        self.assertEqual(result_2["scrobbled_count"], 0)

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


class Phase1TrackerReliabilityTests(TestCase):
    """Kiem thu bo sung Phase 1 cho ingestion count, features_source va enrich flags."""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username="p1_tracker_user", password="pw")

    def test_ingest_mixed_duplicate_and_new_counts_only_new(self):
        payload_1 = {
            "items": [
                {
                    "played_at": "2026-10-01T10:00:00Z",
                    "track": {
                        "id": "p1_tr_1",
                        "name": "Track One",
                        "duration_ms": 200000,
                        "popularity": 70,
                        "artists": [{"id": "p1_art_1", "name": "Artist One"}],
                        "album": {"id": "p1_alb_1", "name": "Album One", "images": []},
                    },
                }
            ]
        }
        payload_2 = {
            "items": [
                {
                    "played_at": "2026-10-01T10:00:00+00:00",
                    "track": payload_1["items"][0]["track"],
                },
                {
                    "played_at": "2026-10-01T10:05:00Z",
                    "track": {
                        "id": "p1_tr_2",
                        "name": "Track Two",
                        "duration_ms": 210000,
                        "popularity": 75,
                        "artists": [{"id": "p1_art_1", "name": "Artist One"}],
                        "album": {"id": "p1_alb_1", "name": "Album One", "images": []},
                    },
                },
            ]
        }
        res1 = ingest_recently_played_payload(self.user, payload_1)
        self.assertEqual(res1["scrobbled_count"], 1)
        res2 = ingest_recently_played_payload(self.user, payload_2)
        self.assertEqual(res2["scrobbled_count"], 1)
        self.assertEqual(ListeningHistory.objects.filter(user=self.user).count(), 2)

    def test_track_features_source_in_serializer_and_spotify_sync(self):
        from unittest.mock import patch, MagicMock
        from tracker.serializers import TrackSerializer
        from tracker.services.ingestion import sync_audio_features_for_unsynced_tracks
        from users.models import SpotifyProfile
        from users.services.encryption import encrypt_token
        from django.utils import timezone
        from datetime import timedelta

        art = Artist.objects.create(spotify_id="p1_fs_art", name="FS Artist")
        tr = Track.objects.create(
            spotify_id="p1_fs_tr",
            name="FS Track",
            duration_ms=180000,
            features_synced=False,
        )
        tr.artists.add(art)

        SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="sp_fs_user",
            display_name="FS User",
            encrypted_access_token=encrypt_token("fake_access_token"),
            encrypted_refresh_token=encrypt_token("fake_refresh_token"),
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "audio_features": [
                {
                    "id": "p1_fs_tr",
                    "danceability": 0.72,
                    "energy": 0.81,
                    "valence": 0.65,
                    "acousticness": 0.12,
                    "instrumentalness": 0.0,
                    "liveness": 0.1,
                    "speechiness": 0.05,
                    "tempo": 124.0,
                }
            ]
        }
        with patch("requests.Session.get", return_value=mock_resp):
            sync_audio_features_for_unsynced_tracks("fake_access_token")

        tr.refresh_from_db()
        self.assertTrue(tr.features_synced)
        self.assertEqual(tr.features_source, "spotify")
        self.assertEqual(TrackSerializer(tr).data["features_source"], "spotify")

    def test_dsp_enrichment_sets_estimated_when_no_preview(self):
        from unittest.mock import patch
        from tracker.services.audio_dsp import enrich_track_with_dsp_and_artwork

        art = Artist.objects.create(spotify_id="p1_dsp_art", name="DSP Artist")
        tr = Track.objects.create(
            spotify_id="p1_dsp_tr",
            name="DSP Fallback Track",
            duration_ms=190000,
            features_synced=False,
        )
        tr.artists.add(art)
        with patch("tracker.services.audio_dsp.discover_track_multimedia", return_value=None):
            enrich_track_with_dsp_and_artwork(tr)

        tr.refresh_from_db()
        self.assertTrue(tr.features_synced)
        self.assertEqual(tr.features_source, "estimated")

    def test_enrich_existing_tracks_command_flags(self):
        from io import StringIO
        from unittest.mock import patch
        from django.core.management import call_command

        Track.objects.create(spotify_id="c_sp", name="Sp", duration_ms=1000, features_synced=True, features_source="spotify")
        Track.objects.create(spotify_id="c_leg", name="Leg", duration_ms=1000, features_synced=True, features_source="legacy_unknown")
        Track.objects.create(spotify_id="c_est", name="Est", duration_ms=1000, features_synced=True, features_source="estimated")
        Track.objects.create(spotify_id="c_un", name="Un", duration_ms=1000, features_synced=False, features_source="unavailable")

        with patch("tracker.management.commands.enrich_existing_tracks.enrich_track_with_dsp_and_artwork", return_value=True) as mock_enrich:
            call_command("enrich_existing_tracks", "--only-missing", stdout=StringIO())
            called_ids = {call.args[0].spotify_id for call in mock_enrich.call_args_list}
            self.assertEqual(called_ids, {"c_un"})

            mock_enrich.reset_mock()
            call_command("enrich_existing_tracks", stdout=StringIO())
            called_ids_default = {call.args[0].spotify_id for call in mock_enrich.call_args_list}
            self.assertEqual(called_ids_default, {"c_leg", "c_est", "c_un"})

            mock_enrich.reset_mock()
            call_command("enrich_existing_tracks", "--force", stdout=StringIO())
            called_ids_force = {call.args[0].spotify_id for call in mock_enrich.call_args_list}
            self.assertEqual(called_ids_force, {"c_sp", "c_leg", "c_est", "c_un"})

    def test_sync_pipeline_two_hour_gap_logs_without_nameerror(self):
        from unittest.mock import patch
        from datetime import timedelta
        from django.utils import timezone
        from tracker.services.ingestion import sync_user_recently_played_pipeline
        from users.models import SpotifyProfile
        from users.services.encryption import encrypt_token

        tr = Track.objects.create(spotify_id="p1_gap_tr", name="Gap Track", duration_ms=180000, features_synced=True)
        ListeningHistory.objects.create(
            user=self.user,
            track=tr,
            played_at=timezone.now() - timedelta(hours=4),
        )
        SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="sp_gap_user",
            display_name="Gap User",
            encrypted_access_token=encrypt_token("fake_access"),
            encrypted_refresh_token=encrypt_token("fake_refresh"),
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

        with patch("tracker.services.ingestion.fetch_recently_played_from_api", return_value={"items": []}), \
             patch("tracker.services.ingestion.sync_audio_features_for_unsynced_tracks", return_value=0):
            res = sync_user_recently_played_pipeline(self.user)

        self.assertEqual(res["scrobbled_count"], 0)


class ManualSyncErrorHandlingTest(TestCase):
    """Kiem thu phan loai loi mang/xac thuc Spotify va co che retry an toan khi sync."""

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from users.services.encryption import encrypt_token

        self.client = APIClient()
        self.user = User.objects.create_user(username="sync_err_user", password="pass_sync_123")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="sp_sync_err",
            display_name="Sync Err User",
            encrypted_access_token=encrypt_token("old_acc"),
            encrypted_refresh_token=encrypt_token("valid_ref"),
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_sync_active=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_manual_sync_maps_timeout_and_upstream_and_auth_and_rate_limit(self):
        import requests
        from tracker.services.ingestion import SpotifyUpstreamError
        from users.services.spotify_auth import SpotifyAuthError

        with patch(
            "tracker.views.sync_user_recently_played_pipeline",
            side_effect=requests.exceptions.ConnectTimeout("timed out"),
        ):
            r_timeout = self.client.post("/api/tracker/sync/")
        self.assertEqual(r_timeout.status_code, status.HTTP_504_GATEWAY_TIMEOUT)
        self.assertIn("error", r_timeout.json())

        with patch(
            "tracker.views.sync_user_recently_played_pipeline",
            side_effect=requests.exceptions.ConnectionError("reset"),
        ):
            r_conn = self.client.post("/api/tracker/sync/")
        self.assertEqual(r_conn.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        with patch(
            "tracker.views.sync_user_recently_played_pipeline",
            side_effect=SpotifyUpstreamError("Spotify 502"),
        ):
            r_up = self.client.post("/api/tracker/sync/")
        self.assertEqual(r_up.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        with patch(
            "tracker.views.sync_user_recently_played_pipeline",
            side_effect=SpotifyAuthError("Token het han"),
        ):
            r_auth = self.client.post("/api/tracker/sync/")
        self.assertEqual(r_auth.status_code, status.HTTP_401_UNAUTHORIZED)

        with patch(
            "tracker.views.sync_user_recently_played_pipeline",
            side_effect=RuntimeError("SPOTIFY_RATE_LIMIT:120"),
        ):
            r_rate = self.client.post("/api/tracker/sync/")
        self.assertEqual(r_rate.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(r_rate.json()["retry_after_seconds"], 120)

    def test_fetch_recently_played_refreshes_once_on_401(self):
        from unittest.mock import MagicMock
        from tracker.services.ingestion import fetch_recently_played_from_api

        resp_401 = MagicMock(status_code=401, headers={}, text="Unauthorized")
        resp_200 = MagicMock(status_code=200, headers={})
        resp_200.json.return_value = {"items": [{"id": "ok"}]}

        mock_session = MagicMock()
        mock_session.get.side_effect = [resp_401, resp_200]

        with patch("tracker.services.ingestion.get_spotify_session", return_value=mock_session), patch(
            "tracker.services.ingestion.refresh_spotify_tokens", return_value="new_tok"
        ) as mock_refresh:
            data = fetch_recently_played_from_api("old_tok", profile=self.profile)

        mock_refresh.assert_called_once_with(self.profile)
        self.assertEqual(mock_session.get.call_count, 2)
        self.assertEqual(mock_session.get.call_args_list[1].kwargs["headers"]["Authorization"], "Bearer new_tok")
        self.assertEqual(data, {"items": [{"id": "ok"}]})

    def test_spotify_session_retry_policy(self):
        from users.services.spotify_auth import get_spotify_session

        sess_retry = get_spotify_session(retries=1)
        retry_cfg = sess_retry.get_adapter("https://").max_retries
        self.assertEqual(retry_cfg.total, 1)
        self.assertEqual(set(retry_cfg.status_forcelist), {500, 502, 503, 504})
        self.assertNotIn(429, retry_cfg.status_forcelist)

        sess_no_retry = get_spotify_session(retries=0)
        no_retry_cfg = sess_no_retry.get_adapter("https://").max_retries
        self.assertEqual(no_retry_cfg.total, 0)

