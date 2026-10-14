"""
Frontend - Backend Contract & Data Transmission Tests
Kiem thu toan dien 100% cac duong truyen du lieu va payload schema giua Frontend va Backend.
Dam bao tinh toan ven hop dong du lieu (Data Contract), chong regression moi khi sua bug/them tinh nang.
"""

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import SpotifyProfile
from users.services.encryption import encrypt_token
from tracker.models import Artist, Album, Track, ListeningHistory
from ai_engine.models import AIMusicPersona


class FrontendBackendContractTests(APITestCase):
    """
    Bo test kiem tra tinh tuong thich tuyet doi giua Backend DRF va Frontend TypeScript.
    Moi endpoint ma frontend/src/services/api.ts goi deu duoc kiem thu chat che ve mat schema.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        # 1. User co day du du lieu lich su
        self.user = User.objects.create_user(
            username='contract_user',
            email='contract@example.com',
            password='TestPassword123!',
        )
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id='spotify_contract_id',
            display_name='Test Contract User',
            email='contract@example.com',
            avatar_url='https://example.com/avatar.jpg',
            encrypted_access_token=encrypt_token('access_tok_123'),
            encrypted_refresh_token=encrypt_token('refresh_tok_123'),
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_sync_active=True,
        )

        # Tao mock artist, album, track va listening history
        self.artist = Artist.objects.create(spotify_id='art_contract_1', name='Son Tung M-TP')
        self.album = Album.objects.create(spotify_id='alb_contract_1', name='Chung Ta', image_url='https://example.com/alb.jpg')
        self.album.artists.add(self.artist)

        self.track = Track.objects.create(
            spotify_id='trk_contract_1',
            name='Chung Ta Cua Tuong Lai',
            duration_ms=240000,
            album=self.album,
            danceability=0.72,
            energy=0.85,
            valence=0.65,
            acousticness=0.15,
            tempo=128.0,
            features_synced=True,
        )
        self.track.artists.add(self.artist)

        now = timezone.now()
        for i in range(5):
            ListeningHistory.objects.create(
                user=self.user,
                track=self.track,
                played_at=now - timedelta(hours=i * 3),
                context_type='playlist',
                raw_spotify_data={'track_name': self.track.name}
            )

        # AI Persona
        self.persona = AIMusicPersona.objects.create(
            user=self.user,
            period_type='monthly',
            persona_title='The Evening Pulse Maestro',
            tagline='Nang luong tran day.',
            vibe_summary='Thich EDM va nhac soi dong.',
            mood_distribution={'energetic': 60, 'melancholic': 20, 'focused': 20},
            recommended_listening_time='20:00 - 23:00',
            ai_advice='Nghe them acoustic.',
            provider_used='groq',
            model_name='test-model',
        )

        # 2. User rong (Zero-Data User) de kiem thu ma tran phong ve Empty State
        self.empty_user = User.objects.create_user(
            username='empty_user',
            email='empty@example.com',
            password='TestPassword123!',
        )
        self.empty_profile = SpotifyProfile.objects.create(
            user=self.empty_user,
            spotify_id='spotify_empty_id',
            display_name='Empty User',
            is_sync_active=True,
        )

    # -------------------------------------------------------------------------
    # 1. KIEM TRA DUONG TRUYEN PROFILE & USER AUTH (/api/users/me/)
    # -------------------------------------------------------------------------
    def test_contract_user_profile(self):
        """Kiem tra hop dong UserProfile tuong thich frontend/src/types/auth.ts."""
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/users/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # Cac truong bat buoc cua UserProfile
        required_fields = [
            'id', 'username', 'email', 'display_name',
            'profile_image_url', 'is_spotify_connected', 'is_sync_active'
        ]
        for field in required_fields:
            self.assertIn(field, data, f"Thieu truong '{field}' trong /api/users/me/ response")

        # Kiem tra Zero-Leakage
        self.assertNotIn('encrypted_access_token', data)
        self.assertNotIn('encrypted_refresh_token', data)
        self.assertEqual(data['profile_image_url'], 'https://example.com/avatar.jpg')
        self.assertTrue(data['is_spotify_connected'])

    # -------------------------------------------------------------------------
    # 2. KIEM TRA DUONG TRUYEN PERIODS LIST (/api/analytics/periods/)
    # -------------------------------------------------------------------------
    def test_contract_analytics_periods(self):
        """Kiem tra hop dong CalendarPeriodsResponse tuong thich types/analytics.ts."""
        self.client.force_authenticate(user=self.user)
        for p_type in ['week', 'month', 'year']:
            res = self.client.get(f'/api/analytics/periods/?period_type={p_type}&limit=12')
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            data = res.json()

            self.assertIn('period_type', data)
            self.assertIn('periods', data)
            self.assertIsInstance(data['periods'], list)
            self.assertGreater(len(data['periods']), 0)

            # Kiem tra tung phan tu CalendarPeriodItem
            item = data['periods'][0]
            for f in ['key', 'label', 'start_date', 'end_date', 'is_current', 'play_count']:
                self.assertIn(f, item, f"Thieu truong '{f}' trong CalendarPeriodItem")
            self.assertIsInstance(item['is_current'], bool)
            self.assertIsInstance(item['play_count'], int)

    # -------------------------------------------------------------------------
    # 3. KIEM TRA DUONG TRUYEN SUMMARY STATS (/api/analytics/summary/)
    # -------------------------------------------------------------------------
    def test_contract_analytics_summary_both_modes(self):
        """Kiem tra hop dong SummaryStats ca voi time_range va start_date/end_date."""
        self.client.force_authenticate(user=self.user)

        # Mode A: Preset time_range
        res_preset = self.client.get('/api/analytics/summary/?time_range=30d')
        self.assertEqual(res_preset.status_code, status.HTTP_200_OK)
        d_preset = res_preset.json()
        for f in ['total_plays', 'total_duration_ms', 'total_hours', 'unique_artists_count', 'unique_albums_count', 'time_range']:
            self.assertIn(f, d_preset, f"Thieu truong '{f}' trong SummaryStats")
        self.assertEqual(d_preset['total_plays'], 5)

        # Mode B: Discrete Calendar Period
        now = timezone.now().date()
        s_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
        e_date = now.strftime('%Y-%m-%d')
        res_dates = self.client.get(f'/api/analytics/summary/?start_date={s_date}&end_date={e_date}')
        self.assertEqual(res_dates.status_code, status.HTTP_200_OK)
        d_dates = res_dates.json()
        self.assertIn('total_plays', d_dates)
        self.assertIsInstance(d_dates['total_hours'], (int, float))

    # -------------------------------------------------------------------------
    # 4. KIEM TRA DUONG TRUYEN TOP TRACKS & TOP ARTISTS
    # -------------------------------------------------------------------------
    def test_contract_top_tracks_and_artists(self):
        """Kiem tra hop dong TopTrack[] va TopArtist[]."""
        self.client.force_authenticate(user=self.user)

        # Top Tracks
        res_tr = self.client.get('/api/analytics/top-tracks/?time_range=30d&limit=5')
        self.assertEqual(res_tr.status_code, status.HTTP_200_OK)
        tr_data = res_tr.json()
        self.assertIn('tracks', tr_data)
        tr_list = tr_data['tracks']
        self.assertIsInstance(tr_list, list)
        self.assertGreater(len(tr_list), 0)
        t_item = tr_list[0]
        for f in ['spotify_id', 'name', 'album_name', 'album_image_url', 'artists', 'play_count']:
            self.assertIn(f, t_item, f"Thieu truong '{f}' trong TopTrack")
        self.assertIsInstance(t_item['artists'], list)

        # Top Artists
        res_ar = self.client.get('/api/analytics/top-artists/?time_range=30d&limit=5')
        self.assertEqual(res_ar.status_code, status.HTTP_200_OK)
        ar_data = res_ar.json()
        self.assertIn('artists', ar_data)
        ar_list = ar_data['artists']
        self.assertIsInstance(ar_list, list)
        self.assertGreater(len(ar_list), 0)
        a_item = ar_list[0]
        for f in ['spotify_id', 'name', 'play_count']:
            self.assertIn(f, a_item, f"Thieu truong '{f}' trong TopArtist")

        # Top Albums
        res_al = self.client.get('/api/analytics/top-albums/?time_range=30d&limit=5')
        self.assertEqual(res_al.status_code, status.HTTP_200_OK)
        al_data = res_al.json()
        self.assertIn('albums', al_data)
        al_list = al_data['albums']
        self.assertIsInstance(al_list, list)
        self.assertGreater(len(al_list), 0)
        al_item = al_list[0]
        for f in ['spotify_id', 'name', 'image_url', 'artists', 'play_count']:
            self.assertIn(f, al_item, f"Thieu truong '{f}' trong TopAlbum")

    # -------------------------------------------------------------------------
    # 5. KIEM TRA DUONG TRUYEN RADAR, HEATMAP, BAR CHART RACE & GENRES
    # -------------------------------------------------------------------------
    def test_contract_visual_analytics(self):
        """Kiem tra hop dong RadarData, HeatmapData, BarChartRaceData, GenreDistributionData."""
        self.client.force_authenticate(user=self.user)

        # Radar
        res_radar = self.client.get('/api/analytics/radar/?time_range=30d')
        self.assertEqual(res_radar.status_code, status.HTTP_200_OK)
        r_data = res_radar.json()
        self.assertIn('features', r_data)
        self.assertIsInstance(r_data['features'], list)
        f_item = r_data['features'][0]
        for f in ['attribute', 'score']:
            self.assertIn(f, f_item, f"Thieu truong '{f}' trong AudioFeatureItem")

        # Heatmap
        res_heat = self.client.get('/api/analytics/heatmap/?time_range=30d')
        self.assertEqual(res_heat.status_code, status.HTTP_200_OK)
        h_data = res_heat.json()
        self.assertIn('matrix', h_data)
        self.assertEqual(len(h_data['matrix']), 168)
        cell = h_data['matrix'][0]
        for f in ['day_of_week', 'hour', 'count']:
            self.assertIn(f, cell, f"Thieu truong '{f}' trong HeatmapCell")

        # Bar Chart Race
        res_race = self.client.get('/api/analytics/bar-chart-race/?time_range=1y&top_n=5')
        self.assertEqual(res_race.status_code, status.HTTP_200_OK)
        race_data = res_race.json()
        self.assertIn('timeline', race_data)
        self.assertIsInstance(race_data['timeline'], list)

        # Weekly Comparison
        res_wc = self.client.get('/api/analytics/weekly-comparison/?time_range=7d')
        self.assertEqual(res_wc.status_code, status.HTTP_200_OK)
        wc_data = res_wc.json()
        for f in ['current_week_label', 'previous_week_label', 'days', 'summary']:
            self.assertIn(f, wc_data, f"Thieu truong '{f}' trong WeeklyComparisonData")
        self.assertEqual(len(wc_data['days']), 7)
        for d in wc_data['days']:
            for df in ['day_index', 'day_name', 'current_week_plays', 'previous_week_plays', 'diff']:
                self.assertIn(df, d)
        for sf in ['total_current_week', 'total_previous_week', 'growth_percentage', 'peak_day_current', 'peak_plays_current']:
            self.assertIn(sf, wc_data['summary'])

        # Genres
        res_genres = self.client.get('/api/analytics/genres/?time_range=30d')
        self.assertEqual(res_genres.status_code, status.HTTP_200_OK)
        g_data = res_genres.json()
        for f in ['genres', 'total_plays', 'top_genre']:
            self.assertIn(f, g_data, f"Thieu truong '{f}' trong GenreDistributionData")
        self.assertIsInstance(g_data['genres'], list)

    # -------------------------------------------------------------------------
    # 6. KIEM TRA DUONG TRUYEN TRACKER HISTORY & STATUS
    # -------------------------------------------------------------------------
    def test_contract_tracker_endpoints(self):
        """Kiem tra hop dong /api/tracker/history/ va /api/tracker/status/."""
        self.client.force_authenticate(user=self.user)

        # History list
        res_hist = self.client.get('/api/tracker/history/?limit=10')
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        h_data = res_hist.json()
        self.assertIn('count', h_data)
        self.assertIn('results', h_data)
        self.assertIsInstance(h_data['results'], list)
        self.assertGreater(len(h_data['results']), 0)
        h_rec = h_data['results'][0]
        for f in ['id', 'track', 'played_at', 'created_at']:
            self.assertIn(f, h_rec, f"Thieu truong '{f}' trong ListeningHistoryRecord")
        self.assertIn('spotify_id', h_rec['track'])
        self.assertIn('name', h_rec['track'])
        self.assertIn('artists', h_rec['track'])

        # Status
        res_status = self.client.get('/api/tracker/status/')
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        s_data = res_status.json()
        for f in ['is_sync_active', 'total_scrobbles']:
            self.assertIn(f, s_data, f"Thieu truong '{f}' trong Tracker Status")

    # -------------------------------------------------------------------------
    # 7. KIEM TRA DUONG TRUYEN AI INSIGHTS & RECOMMENDATIONS
    # -------------------------------------------------------------------------
    def test_contract_ai_endpoints(self):
        """Kiem tra hop dong AIMusicPersona va RecommendationResult."""
        self.client.force_authenticate(user=self.user)

        # Latest Persona
        res_p = self.client.get('/api/ai/persona/latest/?period_type=monthly')
        self.assertEqual(res_p.status_code, status.HTTP_200_OK)
        p_data = res_p.json()
        for f in ['persona_title', 'tagline', 'vibe_summary', 'mood_distribution', 'ai_advice']:
            self.assertIn(f, p_data, f"Thieu truong '{f}' trong AIMusicPersona")
        self.assertIsInstance(p_data['mood_distribution'], dict)

        # Recommendations
        res_rec = self.client.get(f'/api/ai/recommendations/?track_id={self.track.spotify_id}&top_k=5')
        self.assertEqual(res_rec.status_code, status.HTTP_200_OK)
        rec_data = res_rec.json()
        self.assertIn('seed_track', rec_data)
        self.assertIn('recommendations', rec_data)
        self.assertIsInstance(rec_data['recommendations'], list)

    # -------------------------------------------------------------------------
    # 8. MA TRAN PHONG VE ZERO-DATA: USER CHUA CO LICH SU NGHE NAO
    # -------------------------------------------------------------------------
    def test_contract_zero_data_user_graceful_handling(self):
        """Kiem tra tat ca endpoint khong bao gio tra ve 500 khi user co 0 ban ghi nghe."""
        self.client.force_authenticate(user=self.empty_user)

        # 1. Summary
        res_sum = self.client.get('/api/analytics/summary/?time_range=30d')
        self.assertEqual(res_sum.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sum.json()['total_plays'], 0)
        self.assertEqual(res_sum.json()['total_hours'], 0.0)

        # 2. Top Tracks, Artists & Albums
        res_tracks = self.client.get('/api/analytics/top-tracks/?time_range=30d')
        self.assertEqual(res_tracks.status_code, status.HTTP_200_OK)
        self.assertEqual(res_tracks.json()['tracks'], [])

        res_artists = self.client.get('/api/analytics/top-artists/?time_range=30d')
        self.assertEqual(res_artists.status_code, status.HTTP_200_OK)
        self.assertEqual(res_artists.json()['artists'], [])

        res_albums = self.client.get('/api/analytics/top-albums/?time_range=30d')
        self.assertEqual(res_albums.status_code, status.HTTP_200_OK)
        self.assertEqual(res_albums.json()['albums'], [])

        # 2b. Weekly Comparison
        res_wc = self.client.get('/api/analytics/weekly-comparison/?time_range=7d')
        self.assertEqual(res_wc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_wc.json()['summary']['total_current_week'], 0)
        self.assertEqual(res_wc.json()['summary']['total_previous_week'], 0)
        self.assertEqual(len(res_wc.json()['days']), 7)

        # 3. Radar: Mac dinh diem dac trung [0.0, 1.0] de bieu do Radar khong bi sup ve 0 tren FE
        res_radar = self.client.get('/api/analytics/radar/?time_range=30d')
        self.assertEqual(res_radar.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_radar.json()['features']), 5)
        for feat in res_radar.json()['features']:
            self.assertTrue(0.0 <= feat['score'] <= 1.0)

        # 4. Heatmap
        res_heat = self.client.get('/api/analytics/heatmap/?time_range=30d')
        self.assertEqual(res_heat.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_heat.json()['matrix']), 168)
        self.assertEqual(res_heat.json()['max_density'], 0)

        # 5. Genres
        res_genres = self.client.get('/api/analytics/genres/?time_range=30d')
        self.assertEqual(res_genres.status_code, status.HTTP_200_OK)
        self.assertEqual(res_genres.json()['total_plays'], 0)
        self.assertEqual(res_genres.json()['genres'], [])

        # 6. History
        res_hist = self.client.get('/api/tracker/history/')
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        self.assertEqual(res_hist.json()['count'], 0)
        self.assertEqual(res_hist.json()['results'], [])

    # -------------------------------------------------------------------------
    # 9. PHAN QUYEN & BAO VE TOKEN KHI CHUA DANG NHAP (401 UNAUTHORIZED)
    # -------------------------------------------------------------------------
    def test_contract_unauthenticated_rejection(self):
        """Kiem tra toan bo endpoint du lieu ca nhan tu choi truy cap nac danh."""
        self.client.logout()

        protected_urls = [
            '/api/users/me/',
            '/api/tracker/history/',
            '/api/tracker/status/',
            '/api/tracker/sync/',
            '/api/analytics/summary/',
            '/api/analytics/top-tracks/',
            '/api/analytics/top-artists/',
            '/api/analytics/radar/',
            '/api/analytics/heatmap/',
            '/api/analytics/genres/',
            '/api/analytics/periods/',
            '/api/analytics/top-albums/',
            '/api/analytics/weekly-comparison/',
            '/api/ai/persona/latest/',
            '/api/ai/facts/',
        ]

        for url in protected_urls:
            res = self.client.get(url) if 'sync' not in url else self.client.post(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} khong chan truy cap nac danh (HTTP {res.status_code})"
            )

    # -------------------------------------------------------------------------
    # 10. HOP DONG AI MUSIC DETECTIVE FUN FACTS (/api/ai/facts/)
    # -------------------------------------------------------------------------
    def test_contract_ai_music_facts(self):
        """Kiem tra payload hop dong cua Aura Music Detective Fun Facts."""
        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/ai/facts/?period=week')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # 1. Kiem tra top-level keys
        self.assertIn('facts', data)
        self.assertIn('agent_meta', data)
        self.assertTrue(isinstance(data['facts'], list))

        # 2. Kiem tra schema tung Fact item
        required_fact_fields = ['id', 'category', 'badge', 'title', 'description', 'metric_highlight', 'evidence']
        for fact in data['facts']:
            for field in required_fact_fields:
                self.assertIn(field, fact, f"Thieu truong '{field}' trong MusicFact")
            # Kiem tra quy tac khong dung emoji
            for k in ['badge', 'title', 'description', 'metric_highlight']:
                val = str(fact[k])
                self.assertFalse(any(ord(c) > 0x1F600 for c in val), f"Phat hien emoji trong {k}: {val}")
            # Kiem tra xung ho than thien: khong chua 'người dùng'
            self.assertNotIn('người dùng', fact['description'].lower())
            self.assertNotIn('thính giả', fact['description'].lower())

        # 3. Kiem tra agent_meta
        meta = data['agent_meta']
        self.assertIn('agent_name', meta)
        self.assertIn('provider_used', meta)
        self.assertIn('tools_called', meta)
        self.assertTrue(isinstance(meta['tools_called'], list))

    # -------------------------------------------------------------------------
    # 11. HOP DONG MÚI GIỜ ĐỘNG (X-Timezone Header Contract)
    # -------------------------------------------------------------------------
    def test_contract_dynamic_user_timezone(self):
        """Kiem tra Backend chap nhan header X-Timezone tu Frontend khong loi CORS."""
        self.client.force_authenticate(user=self.user)
        # Goi voi timezone Tokyo
        res_tokyo = self.client.get('/api/ai/facts/?period=week', HTTP_X_TIMEZONE='Asia/Tokyo')
        self.assertEqual(res_tokyo.status_code, status.HTTP_200_OK)

        # Goi voi timezone New York
        res_ny = self.client.get('/api/analytics/summary/?time_range=30d', HTTP_X_TIMEZONE='America/New_York')
        self.assertEqual(res_ny.status_code, status.HTTP_200_OK)

        # Goi voi timezone Viet Nam
        res_vn = self.client.get('/api/analytics/weekly-comparison/?time_range=7d', HTTP_X_TIMEZONE='Asia/Ho_Chi_Minh')
        self.assertEqual(res_vn.status_code, status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # 12. HOP DONG TOP ALBUMS VA WEEKLY COMPARISON
    # -------------------------------------------------------------------------
    def test_contract_top_albums_and_weekly_comparison(self):
        """Kiem tra chi tiet payload Top Albums va Weekly Comparison."""
        self.client.force_authenticate(user=self.user)
        # Top Albums
        res_alb = self.client.get('/api/analytics/top-albums/?time_range=30d&limit=5')
        self.assertEqual(res_alb.status_code, status.HTTP_200_OK)
        alb_data = res_alb.json()
        self.assertIn('albums', alb_data)
        for alb in alb_data['albums']:
            for k in ['spotify_id', 'name', 'image_url', 'artists', 'play_count']:
                self.assertIn(k, alb)

        # Weekly Comparison
        res_wc = self.client.get('/api/analytics/weekly-comparison/?time_range=7d')
        self.assertEqual(res_wc.status_code, status.HTTP_200_OK)
        wc_data = res_wc.json()
        self.assertIn('days', wc_data)
        self.assertIn('summary', wc_data)
        self.assertEqual(len(wc_data['days']), 7)
        for day in wc_data['days']:
            for k in ['day_name', 'current_week_plays', 'previous_week_plays']:
                self.assertIn(k, day)
        for sk in ['total_current_week', 'total_previous_week', 'growth_percentage', 'peak_day_current']:
            self.assertIn(sk, wc_data['summary'])

