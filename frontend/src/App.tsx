import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Headphones,
  Clock,
  Mic2,
  Disc,
  Radio,
  ArrowRight,
  CalendarOff,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';

import type { UserProfile } from './types/auth';
import type {
  CalendarPeriodType,
  CalendarPeriodItem,
  SummaryStats,
  TopTrack,
  TopArtist,
  TopAlbum,
  RadarData,
  HeatmapData,
  WeeklyComparisonData,
  GenreDistributionData,
  ListeningHistoryRecord,
} from './types/analytics';
import type { AIMusicPersona, RecommendationResult, MusicFact, AgentMeta } from './types/ai';

import {
  api,
  ApiError,
  type TimeFilterInput,
  MOCK_SUMMARY,
  MOCK_TOP_TRACKS,
  MOCK_TOP_ARTISTS,
  MOCK_TOP_ALBUMS,
  MOCK_RADAR,
  MOCK_HEATMAP,
  MOCK_WEEKLY_COMPARISON,
  MOCK_GENRES,
  MOCK_PERSONA,
  MOCK_LISTENING_HISTORY,
  MOCK_MUSIC_FACTS,
  buildMockRecommendations,
  getDynamicMockCalendarPeriods,
} from './services/api';

import { Navbar } from './components/ui/Navbar';
import { LoginHero } from './components/ui/LoginHero';
import { ToastContainer, type ToastMessage } from './components/ui/Toast';
import { StatCard } from './components/ui/StatCard';
import { CalendarPeriodSelector } from './components/ui/CalendarPeriodSelector';

import { RadarChartComponent } from './components/charts/RadarChartComponent';
import { ListeningHeatmap } from './components/charts/ListeningHeatmap';
import { GenreDistribution } from './components/charts/GenreDistribution';
import { WeeklyComparisonChart } from './components/charts/WeeklyComparisonChart';

import { PersonaCard } from './components/cards/PersonaCard';
import { isValidPersona } from './types/ai';
import { MusicFactsSection } from './components/analytics/MusicFactsSection';
import { CodebaseAssistantSection } from './components/analytics/CodebaseAssistantSection';
import { TopTracksList } from './components/cards/TopTracksList';
import { TopArtistsList } from './components/cards/TopArtistsList';
import { TopAlbumsList } from './components/cards/TopAlbumsList';
import { RecentScrobblesList } from './components/cards/RecentScrobblesList';
import { RecommendationModal } from './components/cards/RecommendationModal';
import { ShareableCard } from './components/cards/ShareableCard';

const EMPTY_SUMMARY: SummaryStats = {
  total_plays: 0,
  total_duration_ms: 0,
  total_hours: 0,
  unique_artists_count: 0,
  unique_albums_count: 0,
  time_range: 'week',
};

const EMPTY_RADAR: RadarData = {
  time_range: 'week',
  total_tracks_analyzed: 0,
  features: [],
};

const EMPTY_HEATMAP: HeatmapData = {
  time_range: 'week',
  period_type: 'week',
  max_density: 0,
  matrix: [],
};

const EMPTY_WEEKLY_COMPARISON: WeeklyComparisonData = {
  time_range: 'week',
  period_type: 'week',
  granularity: 'day',
  current_week_label: '',
  previous_week_label: '',
  days: [],
  summary: {
    total_current: 0,
    total_previous: 0,
    total_current_week: 0,
    total_previous_week: 0,
    growth_percentage: 0,
    baseline_status: 'empty',
    peak_day_current: '',
    peak_plays_current: 0,
  },
};

const EMPTY_GENRES: GenreDistributionData = {
  genres: [],
  total_plays: 0,
  top_genre: 'Chưa có dữ liệu',
};

export function App() {
  // Authentication & Mode State
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authCheckError, setAuthCheckError] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const hasInitializedRef = useRef(false);

  // Toast Notification State
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((type: 'success' | 'error' | 'warning' | 'info', message: string) => {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 6);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismissToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Calendar Period Filter State
  const [periodType, setPeriodType] = useState<CalendarPeriodType>(() => {
    const saved = localStorage.getItem('user_calendar_period_type');
    return (saved === 'week' || saved === 'month' || saved === 'year') ? (saved as CalendarPeriodType) : 'week';
  });
  const [availablePeriods, setAvailablePeriods] = useState<CalendarPeriodItem[]>(() => {
    const dynamicMocks = getDynamicMockCalendarPeriods();
    const saved = localStorage.getItem('user_calendar_period_type') as CalendarPeriodType;
    const type = (saved === 'week' || saved === 'month' || saved === 'year') ? saved : 'week';
    return dynamicMocks[type] || [];
  });
  const [selectedPeriod, setSelectedPeriod] = useState<CalendarPeriodItem | null>(() => {
    const dynamicMocks = getDynamicMockCalendarPeriods();
    const saved = localStorage.getItem('user_calendar_period_type') as CalendarPeriodType;
    const type = (saved === 'week' || saved === 'month' || saved === 'year') ? saved : 'week';
    const savedMode = localStorage.getItem('user_calendar_selected_mode');
    const savedKey = localStorage.getItem('user_calendar_selected_key');
    const periodsForType = dynamicMocks[type] || [];

    if (savedMode === 'specific' && savedKey) {
      const match = periodsForType.find((p) => p.key === savedKey);
      if (match) return match;
    }
    return periodsForType.find((p) => p.is_current) || periodsForType[0] || null;
  });
  const [isLoadingPeriods, setIsLoadingPeriods] = useState(false);

  const handlePeriodTypeChange = (newType: CalendarPeriodType) => {
    setPeriodType(newType);
    localStorage.setItem('user_calendar_period_type', newType);
    localStorage.setItem('user_calendar_selected_mode', 'current');
    localStorage.removeItem('user_calendar_selected_key');

    const dynamicMocks = getDynamicMockCalendarPeriods();
    const defaultPeriod = dynamicMocks[newType]?.find((p) => p.is_current) || dynamicMocks[newType]?.[0] || null;
    if (defaultPeriod) {
      setSelectedPeriod(defaultPeriod);
    }
  };

  const handlePeriodSelect = (period: CalendarPeriodItem) => {
    setSelectedPeriod(period);
    if (period.is_current) {
      localStorage.setItem('user_calendar_selected_mode', 'current');
      localStorage.removeItem('user_calendar_selected_key');
    } else {
      localStorage.setItem('user_calendar_selected_mode', 'specific');
      localStorage.setItem('user_calendar_selected_key', period.key);
    }
  };

  // Analytics Data State (mac dinh rong cho toi khi nap du lieu that hoac bat Demo Mode)
  const [summary, setSummary] = useState<SummaryStats>(EMPTY_SUMMARY);
  const [topTracks, setTopTracks] = useState<TopTrack[]>([]);
  const [topArtists, setTopArtists] = useState<TopArtist[]>([]);
  const [topAlbums, setTopAlbums] = useState<TopAlbum[]>([]);
  const [radarData, setRadarData] = useState<RadarData>(EMPTY_RADAR);
  const [heatmapData, setHeatmapData] = useState<HeatmapData>(EMPTY_HEATMAP);
  const [weeklyComparison, setWeeklyComparison] = useState<WeeklyComparisonData>(EMPTY_WEEKLY_COMPARISON);
  const [genreData, setGenreData] = useState<GenreDistributionData>(EMPTY_GENRES);
  const [recentScrobbles, setRecentScrobbles] = useState<ListeningHistoryRecord[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // AI Persona & Recommendations State
  const [persona, setPersona] = useState<AIMusicPersona | null>(null);
  const [isGeneratingPersona, setIsGeneratingPersona] = useState(false);

  // Music Facts Detective Agent State
  const [musicFacts, setMusicFacts] = useState<MusicFact[]>([]);
  const [agentMeta, setAgentMeta] = useState<AgentMeta | undefined>(undefined);
  const [isLoadingFacts, setIsLoadingFacts] = useState(false);

  // Modals & Action States
  const [isSyncing, setIsSyncing] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isRecModalOpen, setIsRecModalOpen] = useState(false);
  const [recData, setRecData] = useState<RecommendationResult | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);

  // Anti-Spam Rate Limit Cooldown States
  const [personaCooldown, setPersonaCooldown] = useState(0);
  const [factsCooldown, setFactsCooldown] = useState(0);

  useEffect(() => {
    if (factsCooldown <= 0) return;
    const timer = setTimeout(() => setFactsCooldown((prev) => prev - 1), 1000);
    return () => clearTimeout(timer);
  }, [factsCooldown]);

  useEffect(() => {
    if (personaCooldown <= 0) return;
    const timer = setTimeout(() => setPersonaCooldown((prev) => prev - 1), 1000);
    return () => clearTimeout(timer);
  }, [personaCooldown]);

  // 1. Fetch User & Analytics Data tu Backend theo khoang thoi gian duoc chon
  const refreshAllData = useCallback(async (period: CalendarPeriodItem | null) => {
    if (!user) {
      if (isDemoMode) {
        setHeatmapData((prev) => ({
          ...prev,
          period_type: periodType,
        }));
      }
      return;
    }

    setAnalyticsError(null);

    let timeFilter: TimeFilterInput = '30d';
    if (period) {
      if (periodType === 'month' && period.start_date && period.end_date) {
        const s = new Date(period.start_date);
        const e = new Date(period.end_date);
        const diffDays = Math.round((e.getTime() - s.getTime()) / (1000 * 3600 * 24));
        if (diffDays > 32) {
          const y = e.getFullYear();
          const m = (e.getMonth() + 1).toString().padStart(2, '0');
          const lastD = new Date(y, e.getMonth() + 1, 0).getDate().toString().padStart(2, '0');
          timeFilter = { start_date: `${y}-${m}-01`, end_date: `${y}-${m}-${lastD}` };
        } else {
          timeFilter = { start_date: period.start_date, end_date: period.end_date };
        }
      } else {
        timeFilter = { start_date: period.start_date, end_date: period.end_date };
      }
    }

    const results = await Promise.allSettled([
      api.getSummary(timeFilter),
      api.getTopTracks(timeFilter, 5),
      api.getTopArtists(timeFilter, 5),
      api.getTopAlbums(timeFilter, 5),
      api.getRadar(timeFilter),
      api.getHeatmap(timeFilter, periodType),
      api.getWeeklyComparison(timeFilter, periodType),
      api.getGenreDistribution(timeFilter),
      api.getLatestPersona('monthly'),
      api.getListeningHistory(20),
      api.getMusicFacts(period?.key || 'week', false, false),
    ]);

    const [
      sumRes,
      tracksRes,
      artistsRes,
      albumsRes,
      radarRes,
      heatmapRes,
      compRes,
      genresRes,
      personaRes,
      historyRes,
      factsRes,
    ] = results;

    if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
    if (tracksRes.status === 'fulfilled') setTopTracks(tracksRes.value);
    if (artistsRes.status === 'fulfilled') setTopArtists(artistsRes.value);
    if (albumsRes.status === 'fulfilled') setTopAlbums(albumsRes.value);
    if (radarRes.status === 'fulfilled') setRadarData(radarRes.value);
    if (heatmapRes.status === 'fulfilled') setHeatmapData(heatmapRes.value);
    if (compRes.status === 'fulfilled') setWeeklyComparison(compRes.value);
    if (genresRes.status === 'fulfilled') setGenreData(genresRes.value);
    if (personaRes.status === 'fulfilled') {
      setPersona(isValidPersona(personaRes.value) ? personaRes.value : null);
    }
    if (historyRes.status === 'fulfilled') setRecentScrobbles(historyRes.value);
    if (factsRes.status === 'fulfilled' && factsRes.value && Array.isArray(factsRes.value.facts)) {
      setMusicFacts(factsRes.value.facts);
      setAgentMeta(factsRes.value.agent_meta);
    }

    const rejected = results
      .filter((r): r is PromiseRejectedResult => r.status === 'rejected')
      .map((r) => r.reason);

    if (rejected.length > 0) {
      const hasUnauthorized = rejected.some(
        (reason) => reason instanceof ApiError && reason.status === 401
      );
      if (hasUnauthorized) {
        localStorage.removeItem('access_token');
        setUser(null);
        addToast('warning', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập Spotify lại.');
        return;
      }

      const firstMsg =
        rejected[0] instanceof Error
          ? rejected[0].message
          : 'Không thể tải đầy đủ dữ liệu phân tích từ máy chủ.';
      setAnalyticsError(firstMsg);
    }
  }, [user, isDemoMode, periodType, addToast]);

  const checkSession = useCallback(async () => {
    setIsCheckingAuth(true);
    setAuthCheckError(null);
    try {
      const currentUser = await api.getCurrentUser();
      if (currentUser) {
        setUser(currentUser);
        setIsDemoMode(false);
      } else {
        setUser(null);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Lỗi kết nối máy chủ xác thực.';
      setAuthCheckError(msg);
    } finally {
      setIsCheckingAuth(false);
    }
  }, []);

  // 2. Kiem tra OAuth Callback (one-time exchange_code) & Token khi ung dung khoi tao
  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    const params = new URLSearchParams(window.location.search);
    const exchangeCode = params.get('exchange_code');
    const authSuccess = params.get('auth_success');
    const authError = params.get('auth_error');

    if (authError) {
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => {
        addToast('error', decodeURIComponent(authError));
      }, 0);
    }

    if (exchangeCode) {
      window.history.replaceState({}, document.title, window.location.pathname);
      api.exchangeSpotifyCode(exchangeCode)
        .then((res) => {
          localStorage.setItem('access_token', res.token);
          setUser(res.user);
          setIsDemoMode(false);
          setAuthCheckError(null);
          addToast('success', 'Đăng nhập Spotify thành công! Đang tải hồ sơ của bạn...');
        })
        .catch((err) => {
          const msg = err instanceof Error ? err.message : 'Trao đổi phiên đăng nhập thất bại.';
          addToast('error', msg);
        })
        .finally(() => {
          setIsCheckingAuth(false);
        });
      return;
    }

    if (authSuccess) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Kiem tra phien lam viec hien tai - KHONG goi triggerSync o day de tranh block spinner
    api.getCurrentUser()
      .then((currentUser) => {
        if (currentUser) {
          setUser(currentUser);
          setIsDemoMode(false);
          if (authSuccess) {
            addToast('success', 'Đăng nhập Spotify thành công! Đang tải hồ sơ của bạn...');
          }
        }
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : 'Không thể xác minh phiên làm việc.';
        setAuthCheckError(msg);
      })
      .finally(() => {
        setIsCheckingAuth(false);
      });
  }, [addToast]);

  // 3. Load danh sach ky thoi gian (Available Periods) khi periodType hoac user thay doi
  useEffect(() => {
    if (!user && !isDemoMode) return;
    let isCancelled = false;

    const fetchPeriods = async () => {
      if (isDemoMode && !user) {
        const dynamicMocks = getDynamicMockCalendarPeriods();
        const mockPeriods = dynamicMocks[periodType] || [];
        setAvailablePeriods(mockPeriods);
        setSelectedPeriod(mockPeriods.find((p) => p.is_current) || mockPeriods[0] || null);
        return;
      }

      setIsLoadingPeriods(true);
      try {
        const periods = await api.getAvailablePeriods(periodType, 12);
        if (!isCancelled && periods.length > 0) {
          setAvailablePeriods(periods);
          setSelectedPeriod((prev) => {
            const savedMode = localStorage.getItem('user_calendar_selected_mode');
            const savedKey = localStorage.getItem('user_calendar_selected_key');

            if (savedMode === 'specific' && savedKey) {
              const matchedSaved = periods.find((p) => p.key === savedKey);
              if (matchedSaved) return matchedSaved;
            }

            if (prev && !prev.is_current && savedMode === 'specific') {
              const matchedPrev = periods.find((p) => p.key === prev.key);
              if (matchedPrev) return matchedPrev;
            }

            const current = periods.find((p) => p.is_current);
            return current || periods[0];
          });
        }
      } catch (err) {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Không thể tải danh sách kỳ thống kê.';
          setAnalyticsError(msg);
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingPeriods(false);
        }
      }
    };

    fetchPeriods();
    return () => {
      isCancelled = true;
    };
  }, [user, isDemoMode, periodType]);

  // 4. Tu dong tai du lieu phan tich khi selectedPeriod thay doi
  useEffect(() => {
    if (!user || !selectedPeriod) return;
    let isCancelled = false;

    const loadData = async () => {
      if (!isCancelled) {
        await refreshAllData(selectedPeriod);
      }
    };

    loadData();
    return () => {
      isCancelled = true;
    };
  }, [user, selectedPeriod, refreshAllData]);

  // 5. Auto-sync Spotify 1 lan duy nhat sau khi xac nhan user
  const hasAutoSyncedRef = useRef(false);
  useEffect(() => {
    if (!user || hasAutoSyncedRef.current) return;
    hasAutoSyncedRef.current = true;

    const runAutoSync = async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} lượt nghe mới!`);
          const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
          setAvailablePeriods(updatedPeriods);
          const activePeriod = (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) || updatedPeriods[0] || null;
          setSelectedPeriod(activePeriod);
          refreshAllData(activePeriod);
        }
      } catch {
        // Bo qua loi sync ngam
      }
    };
    runAutoSync();
  }, [user, addToast, refreshAllData, selectedPeriod, periodType]);

  // 6. Periodic background auto-sync moi 15 phut khi tab dang mo
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} bài hát mới từ Spotify.`);
          const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
          setAvailablePeriods(updatedPeriods);
          const activePeriod = (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) || updatedPeriods[0] || null;
          setSelectedPeriod(activePeriod);
          refreshAllData(activePeriod);
        }
      } catch {
        // Bo qua loi polling ngam
      }
    }, 900000);

    return () => clearInterval(interval);
  }, [user, selectedPeriod, periodType, refreshAllData, addToast]);

  // Handlers
  const handleLogin = async () => {
    setIsLoggingIn(true);
    try {
      const authUrl = await api.getLoginUrl();
      if (authUrl && authUrl !== '#') {
        window.location.href = authUrl;
      } else {
        addToast('error', 'Không thể khởi tạo đường dẫn đăng nhập Spotify. Vui lòng kiểm tra Backend.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Lỗi kết nối máy chủ xác thực.';
      addToast('error', msg);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setIsDemoMode(false);
      addToast('info', 'Bạn đã đăng xuất thành công.');
    }
  };

  const handleEnterDemo = () => {
    setIsDemoMode(true);
    setAnalyticsError(null);
    localStorage.setItem('user_calendar_selected_mode', 'current');
    localStorage.removeItem('user_calendar_selected_key');
    const dynamicMocks = getDynamicMockCalendarPeriods();
    setPeriodType('week');
    setAvailablePeriods(dynamicMocks.week);
    setSelectedPeriod(dynamicMocks.week[0]);
    setSummary(MOCK_SUMMARY);
    setTopTracks(MOCK_TOP_TRACKS);
    setTopArtists(MOCK_TOP_ARTISTS);
    setTopAlbums(MOCK_TOP_ALBUMS);
    setRadarData(MOCK_RADAR);
    setHeatmapData(MOCK_HEATMAP);
    setWeeklyComparison(MOCK_WEEKLY_COMPARISON);
    setGenreData(MOCK_GENRES);
    setRecentScrobbles(MOCK_LISTENING_HISTORY);
    setPersona(MOCK_PERSONA);
    setMusicFacts(MOCK_MUSIC_FACTS.facts);
    setAgentMeta(MOCK_MUSIC_FACTS.agent_meta);
    addToast('info', 'Đã bật Chế độ Xem thử (Demo) với dữ liệu mẫu.');
  };

  const handleExitDemo = () => {
    setIsDemoMode(false);
    setSummary(EMPTY_SUMMARY);
    setTopTracks([]);
    setTopArtists([]);
    setTopAlbums([]);
    setRadarData(EMPTY_RADAR);
    setHeatmapData(EMPTY_HEATMAP);
    setWeeklyComparison(EMPTY_WEEKLY_COMPARISON);
    setGenreData(EMPTY_GENRES);
    setRecentScrobbles([]);
    setPersona(null);
    setMusicFacts([]);
    setAgentMeta(undefined);
  };

  const handleSync = async () => {
    if (isDemoMode && !user) {
      addToast('warning', 'Chế độ Xem thử không đồng bộ bài hát thật. Vui lòng đăng nhập Spotify để đồng bộ.');
      return;
    }

    setIsSyncing(true);
    try {
      const res = await api.triggerSync();
      const count = res.scrobbled_count ?? 0;
      addToast('success', `Đồng bộ thành công! Đã ghi nhận ${count} bài hát mới từ Spotify.`);
      const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
      setAvailablePeriods(updatedPeriods);
      const activePeriod = (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) || updatedPeriods[0] || null;
      setSelectedPeriod(activePeriod);
      await refreshAllData(activePeriod);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { error?: string } } };
      if (axiosErr?.response?.status === 429) {
        const rateLimitMsg = axiosErr.response.data?.error || 'Spotify đang tạm giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau.';
        addToast('warning', rateLimitMsg);
      } else {
        const msg = err instanceof Error ? err.message : 'Lỗi kết nối';
        addToast('error', `Đồng bộ thất bại: ${msg}`);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRegeneratePersona = async () => {
    if (isDemoMode && !user) {
      addToast('info', 'Bạn đang ở chế độ xem thử. Dữ liệu AI Persona mẫu đang hiển thị.');
      return;
    }
    if (personaCooldown > 0) {
      addToast('warning', `Vui lòng đợi ${personaCooldown}s trước khi phân tích lại.`);
      return;
    }

    setIsGeneratingPersona(true);
    try {
      const newPersona = await api.generatePersona('monthly');
      if (newPersona) {
        setPersona(newPersona);
        setPersonaCooldown(15);
        if (newPersona.provider_used?.includes('backup')) {
          addToast('info', 'Đã phân tích AI Persona thành công qua model dự phòng (Groq 20B)!');
        } else {
          addToast('success', 'Đã phân tích và cập nhật AI Persona mới thành công!');
        }
      }
    } catch {
      addToast('error', 'Không thể tạo AI Persona. Vui lòng kiểm tra API Key.');
    } finally {
      setIsGeneratingPersona(false);
    }
  };

  const handleRefreshFacts = async () => {
    if (isDemoMode && !user) {
      addToast('info', 'Bạn đang ở chế độ xem thử. Dữ liệu sự thật âm nhạc mẫu đang hiển thị.');
      return;
    }
    if (factsCooldown > 0) {
      addToast('warning', `Vui lòng đợi ${factsCooldown}s trước khi điều tra lại.`);
      return;
    }

    setIsLoadingFacts(true);
    try {
      const res = await api.getMusicFacts(selectedPeriod?.key || 'week', true, true);
      if (res && Array.isArray(res.facts)) {
        setMusicFacts(res.facts);
        setAgentMeta(res.agent_meta);
        setFactsCooldown(15);
        if (res.agent_meta?.provider_used?.includes('backup')) {
          addToast('info', 'Aura Detective Agent đã dùng model dự phòng (Groq 20B) để điều tra thành công!');
        } else if (res.agent_meta?.provider_used?.includes('groq')) {
          addToast('success', 'Aura Detective Agent đã điều tra và cập nhật các sự thật mới!');
        } else {
          addToast('info', 'AI đang hồi phục hạn mức, hệ thống đã dùng phân tích nội bộ tìm ra các sự thật này.');
        }
      }
    } catch {
      addToast('error', 'Không thể làm mới sự thật âm nhạc lúc này.');
    } finally {
      setIsLoadingFacts(false);
    }
  };

  const handleRefreshHistory = async () => {
    if (isDemoMode && !user) {
      addToast('info', 'Bạn đang ở chế độ xem thử.');
      return;
    }
    setIsLoadingHistory(true);
    try {
      const history = await api.getListeningHistory(20);
      setRecentScrobbles(history);
      addToast('info', 'Đã làm mới danh sách bài hát gần đây.');
    } catch {
      addToast('error', 'Không thể làm mới lịch sử nghe nhạc.');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleFindSimilarSongs = async (trackId: string) => {
    setIsRecModalOpen(true);
    setIsLoadingRecs(true);
    setRecData(null);
    if (isDemoMode && !user) {
      setRecData(buildMockRecommendations(trackId));
      setIsLoadingRecs(false);
      return;
    }
    try {
      const res = await api.getRecommendations(trackId, 5);
      setRecData(res);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Không thể tìm bài hát tương tự.';
      addToast('error', msg);
      setIsRecModalOpen(false);
    } finally {
      setIsLoadingRecs(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-[#F8FAFC]">
      {/* Top Navbar */}
      <Navbar
        user={user}
        isDemoMode={isDemoMode}
        isSyncing={isSyncing}
        onSync={handleSync}
        onLogout={handleLogout}
        onLogin={handleLogin}
        onExitDemo={handleExitDemo}
      />

      {/* Main Content View */}
      {isCheckingAuth ? (
        <div className="min-h-[80vh] flex flex-col items-center justify-center space-y-4">
          <div className="w-10 h-10 border-2 border-[#1DB954] border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Đang kiểm tra phiên làm việc...</p>
        </div>
      ) : authCheckError && !user && !isDemoMode ? (
        <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="max-w-md space-y-1.5">
            <h2 className="text-lg font-bold text-white">Không thể kết nối máy chủ xác thực</h2>
            <p className="text-xs sm:text-sm text-slate-400">{authCheckError}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={checkSession}
              className="px-4 py-2 rounded-xl text-xs font-bold bg-[#1DB954] text-black hover:bg-[#1ED760] transition-all cursor-pointer"
            >
              Thử lại
            </button>
            <button
              onClick={handleEnterDemo}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#131B2E] border border-[#1E293B] text-slate-300 hover:text-white transition-all cursor-pointer"
            >
              Xem thử Demo
            </button>
          </div>
        </div>
      ) : !user && !isDemoMode ? (
        /* Màn hình Chào mừng & Đăng nhập khi chưa xác thực */
        <LoginHero
          onLogin={handleLogin}
          onEnterDemo={handleEnterDemo}
          isLoading={isLoggingIn}
        />
      ) : (
        /* Màn hình Bảng Điều Khiển Dashboard */
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in duration-300">
          {/* Demo Mode Notice Banner */}
          {isDemoMode && (
            <div className="p-4 rounded-2xl bg-amber-950/40 border border-amber-800/60 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-3 text-left">
                <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                  <Radio className="w-4 h-4 animate-pulse" />
                </div>
                <div>
                  <h2 className="text-xs sm:text-sm font-bold text-amber-200">
                    Bạn đang ở Chế độ Xem thử (Demo Mode)
                  </h2>
                  <p className="text-[11px] sm:text-xs text-amber-300/80">
                    Toàn bộ biểu đồ và chỉ số đang phản ánh dữ liệu mẫu. Kết nối tài khoản Spotify của bạn để theo dõi dữ liệu thực tế.
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogin}
                className="shrink-0 flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#1DB954] text-black hover:bg-[#1ED760] transition-all cursor-pointer shadow-md shadow-[#1DB954]/20"
              >
                <span>Đăng nhập Spotify ngay</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Dashboard Header & Calendar Period Filter */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#1E293B] gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                Bảng Phân Tích Thống Kê Âm Nhạc
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Theo dõi thói quen nghe nhạc, các chỉ số Audio Features và cá tính AI Persona
              </p>
            </div>

            <CalendarPeriodSelector
              periodType={periodType}
              onPeriodTypeChange={handlePeriodTypeChange}
              selectedPeriod={selectedPeriod}
              onPeriodSelect={handlePeriodSelect}
              periods={availablePeriods}
              isLoading={isLoadingPeriods}
            />
          </div>

          {analyticsError && user && (
            <div className="p-4 rounded-2xl bg-rose-950/35 border border-rose-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-xs sm:text-sm font-bold text-rose-200">
                    Không thể tải đầy đủ dữ liệu thống kê từ máy chủ
                  </h2>
                  <p className="text-[11px] sm:text-xs text-rose-300/80">
                    {analyticsError}
                  </p>
                </div>
              </div>
              <button
                onClick={() => refreshAllData(selectedPeriod)}
                className="shrink-0 inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-rose-500/20 hover:bg-rose-500/30 text-rose-100 border border-rose-500/30 transition-all cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Thử lại</span>
              </button>
            </div>
          )}

          {/* 1. Quick Stats Overview Grid */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <StatCard
              title="Tổng Lượt Nghe"
              value={summary.total_plays.toLocaleString()}
              subtitle={selectedPeriod ? selectedPeriod.label : 'Trong kỳ này'}
              icon={<Headphones className="w-5 h-5" />}
            />
            <StatCard
              title="Thời Lượng Nghe Ước Tính"
              value={`${summary.total_hours} giờ`}
              subtitle="Tổng thời lượng các bài đã phát"
              icon={<Clock className="w-5 h-5" />}
            />
            <StatCard
              title="Nghệ Sĩ Đã Nghe"
              value={summary.unique_artists_count}
              subtitle="Nghệ sĩ độc nhất"
              icon={<Mic2 className="w-5 h-5" />}
            />
            <StatCard
              title="Album Đã Thưởng Thức"
              value={summary.unique_albums_count}
              subtitle="Album / Đĩa đơn độc nhất"
              icon={<Disc className="w-5 h-5" />}
            />
          </section>

          {/* Dieu kien hien thi: Neu khong co luot nghe nao trong ky duoc chon */}
          {summary.total_plays === 0 ? (
            /* Giao dien dac thu khi chua co du lieu nghe trong ky nay */
            <section className="p-8 sm:p-12 rounded-2xl bg-[#131B2E] border border-[#1E293B] text-center flex flex-col items-center justify-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400">
                <CalendarOff className="w-7 h-7" />
              </div>
              <div className="max-w-md space-y-2">
                <h3 className="text-base sm:text-lg font-bold text-white">
                  Bạn chưa có dữ liệu nghe trong khoảng thời gian này
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
                  Spotify chưa ghi nhận lượt nghe nào của bạn trong {selectedPeriod?.label || 'kỳ thống kê này'}. Hãy chọn một khoảng thời gian khác hoặc quay lại kỳ hiện tại để xem phân tích chi tiết.
                </p>
              </div>
              {availablePeriods.length > 0 && (
                <button
                  onClick={() => {
                    const current = availablePeriods.find((p) => p.is_current) || availablePeriods[0];
                    if (current) handlePeriodSelect(current);
                  }}
                  className="mt-2 inline-flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#1DB954] text-black hover:bg-[#1ED760] transition-all cursor-pointer shadow-md shadow-[#1DB954]/20"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Quay lại kỳ hiện tại</span>
                </button>
              )}
            </section>
          ) : (
            <>
              {/* 2. Highlight AI Persona Card */}
              <section>
                <PersonaCard
                  persona={persona}
                  isGenerating={isGeneratingPersona}
                  onRegenerate={handleRegeneratePersona}
                  onOpenShareModal={() => setIsShareModalOpen(true)}
                  cooldownSeconds={personaCooldown}
                />
              </section>

              {/* 2.1 AI Music Detective Facts Section */}
              <section>
                <MusicFactsSection
                  facts={musicFacts}
                  agentMeta={agentMeta}
                  periodLabel={selectedPeriod ? selectedPeriod.label : 'Tuần này'}
                  isLoading={isLoadingFacts}
                  onRefresh={handleRefreshFacts}
                  cooldownSeconds={factsCooldown}
                />
              </section>

              {/* 2.2 Codebase & System Architecture Intelligence RAG Section */}
              <section>
                <CodebaseAssistantSection onAddToast={addToast} isAdmin={Boolean(user?.is_staff)} />
              </section>

              {/* 3. Deep Visual Analytics: Radar & 24x7 Heatmap */}
              <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-5 flex">
                  <RadarChartComponent
                    data={radarData.features}
                    totalTracksAnalyzed={radarData.total_tracks_analyzed}
                    provenance={radarData.provenance}
                  />
                </div>
                <div className="lg:col-span-7 flex">
                  <ListeningHeatmap
                    data={heatmapData.matrix}
                    periodType={periodType}
                    monthCalendar={heatmapData.month_calendar}
                    yearCalendar={heatmapData.year_calendar}
                    selectedPeriodLabel={selectedPeriod?.label}
                  />
                </div>
              </section>

              {/* 4. Thể Loại Âm Nhạc Chủ Đạo (Top Genres Stream Distribution) */}
              <section>
                <GenreDistribution data={genreData} />
              </section>

              {/* 5. Top Charts: Tracks, Artists & Albums */}
              <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <TopTracksList tracks={topTracks} onFindSimilar={handleFindSimilarSongs} />
                <TopArtistsList artists={topArtists} />
                <TopAlbumsList albums={topAlbums} />
              </section>

              {/* 7. Biểu Đồ So Sánh Xu Hướng Nghe Nhạc Thích Ứng */}
              <section>
                <WeeklyComparisonChart data={weeklyComparison} periodType={periodType} />
              </section>
            </>
          )}

          {/* 6. Nhật Ký Nghe Nhạc Gần Đây (Recent Scrobbles) Luon hien thi ben duoi */}
          <section>
            <RecentScrobblesList
              records={recentScrobbles}
              isLoading={isLoadingHistory}
              onRefresh={handleRefreshHistory}
              onFindSimilar={handleFindSimilarSongs}
            />
          </section>
        </main>
      )}

      {/* Footer */}
      <footer className="w-full bg-[#0B0F17] border-t border-[#1E293B] mt-16 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4">
          <p>
            Dự án Music Analytics Dashboard - Tích hợp Spotify API, Groq AI và Scikit-Learn
          </p>
          <p>
            Giao diện Obsidian Dark Mode (#0B0F17) - React 19 + TypeScript + Tailwind v4
          </p>
        </div>
      </footer>

      {/* Modal Xuat The Chia Se */}
      <ShareableCard
        userName={user?.display_name || user?.username || 'Thính giả Demo'}
        avatarUrl={user?.profile_image_url || undefined}
        personaTitle={persona?.persona_title || 'Người Khám Phá Âm Nhạc'}
        tagline={persona?.tagline || 'Âm nhạc phản chiếu tâm hồn và nhịp sống của riêng bạn.'}
        topArtists={topArtists.map((a) => a.name)}
        topGenres={genreData.genres.map((g) => g.name)}
        period={selectedPeriod ? selectedPeriod.label : 'Kỳ thống kê'}
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        totalPlays={summary.total_plays}
        totalHours={summary.total_hours}
        topGenre={genreData.genres[0]?.name}
        topTrack={
          topTracks[0]
            ? {
                name: topTracks[0].name,
                artist: Array.isArray(topTracks[0].artists)
                  ? topTracks[0].artists.join(', ')
                  : 'Nghệ sĩ',
                playCount: topTracks[0].play_count,
                imageUrl: topTracks[0].album_image_url,
              }
            : undefined
        }
        topArtist={
          topArtists[0]
            ? {
                name: topArtists[0].name,
                playCount: topArtists[0].play_count,
                imageUrl: topArtists[0].image_url,
              }
            : undefined
        }
        topAlbum={
          topAlbums[0]
            ? {
                name: topAlbums[0].name,
                artist: Array.isArray(topAlbums[0].artists)
                  ? topAlbums[0].artists.join(', ')
                  : 'Nhiều nghệ sĩ',
                playCount: topAlbums[0].play_count,
                imageUrl: topAlbums[0].image_url,
              }
            : undefined
        }
      />

      {/* Modal Goi Y Bai Hat KNN */}
      <RecommendationModal
        isOpen={isRecModalOpen}
        onClose={() => setIsRecModalOpen(false)}
        data={recData}
        isLoading={isLoadingRecs}
      />

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default App;
