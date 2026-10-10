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
} from 'lucide-react';

import type { UserProfile } from './types/auth';
import type {
  CalendarPeriodType,
  CalendarPeriodItem,
  SummaryStats,
  TopTrack,
  TopArtist,
  RadarData,
  HeatmapData,
  BarChartRaceData,
  GenreDistributionData,
  ListeningHistoryRecord,
} from './types/analytics';
import type { AIMusicPersona, RecommendationResult } from './types/ai';

import {
  api,
  type TimeFilterInput,
  MOCK_SUMMARY,
  MOCK_TOP_TRACKS,
  MOCK_TOP_ARTISTS,
  MOCK_RADAR,
  MOCK_HEATMAP,
  MOCK_RACE,
  MOCK_GENRES,
  MOCK_PERSONA,
  MOCK_LISTENING_HISTORY,
  MOCK_CALENDAR_PERIODS,
} from './services/api';

import { Navbar } from './components/ui/Navbar';
import { LoginHero } from './components/ui/LoginHero';
import { ToastContainer, type ToastMessage } from './components/ui/Toast';
import { StatCard } from './components/ui/StatCard';
import { CalendarPeriodSelector } from './components/ui/CalendarPeriodSelector';

import { RadarChartComponent } from './components/charts/RadarChartComponent';
import { ListeningHeatmap } from './components/charts/ListeningHeatmap';
import { GenreDistribution } from './components/charts/GenreDistribution';
import { BarChartRace } from './components/charts/BarChartRace';

import { PersonaCard } from './components/cards/PersonaCard';
import { TopTracksList } from './components/cards/TopTracksList';
import { TopArtistsList } from './components/cards/TopArtistsList';
import { RecentScrobblesList } from './components/cards/RecentScrobblesList';
import { RecommendationModal } from './components/cards/RecommendationModal';
import { ShareableCard } from './components/cards/ShareableCard';

export function App() {
  // Authentication & Mode State
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
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
  const [availablePeriods, setAvailablePeriods] = useState<CalendarPeriodItem[]>(() => MOCK_CALENDAR_PERIODS['week'] || []);
  const [selectedPeriod, setSelectedPeriod] = useState<CalendarPeriodItem | null>(() => (MOCK_CALENDAR_PERIODS['week'] ? MOCK_CALENDAR_PERIODS['week'][0] : null));
  const [isLoadingPeriods, setIsLoadingPeriods] = useState(false);

  const handlePeriodTypeChange = (newType: CalendarPeriodType) => {
    setPeriodType(newType);
    localStorage.setItem('user_calendar_period_type', newType);
  };

  const handlePeriodSelect = (period: CalendarPeriodItem) => {
    setSelectedPeriod(period);
  };

  // Analytics Data State
  const [summary, setSummary] = useState<SummaryStats>(MOCK_SUMMARY);
  const [topTracks, setTopTracks] = useState<TopTrack[]>(MOCK_TOP_TRACKS);
  const [topArtists, setTopArtists] = useState<TopArtist[]>(MOCK_TOP_ARTISTS);
  const [radarData, setRadarData] = useState<RadarData>(MOCK_RADAR);
  const [heatmapData, setHeatmapData] = useState<HeatmapData>(MOCK_HEATMAP);
  const [raceData, setRaceData] = useState<BarChartRaceData>(MOCK_RACE);
  const [genreData, setGenreData] = useState<GenreDistributionData>(MOCK_GENRES);
  const [recentScrobbles, setRecentScrobbles] = useState<ListeningHistoryRecord[]>(MOCK_LISTENING_HISTORY);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // AI Persona & Recommendations State
  const [persona, setPersona] = useState<AIMusicPersona>(MOCK_PERSONA);
  const [isGeneratingPersona, setIsGeneratingPersona] = useState(false);

  // Modals & Action States
  const [isSyncing, setIsSyncing] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isRecModalOpen, setIsRecModalOpen] = useState(false);
  const [recData, setRecData] = useState<RecommendationResult | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);

  // 1. Fetch User & Analytics Data tu Backend theo khoang thoi gian duoc chon
  const refreshAllData = useCallback(async (period: CalendarPeriodItem | null) => {
    if (!user) return;
    try {
      const timeFilter: TimeFilterInput = period
        ? { start_date: period.start_date, end_date: period.end_date }
        : '30d';

      const [sum, tracks, artists, radar, heatmap, race, genres, p, history] = await Promise.all([
        api.getSummary(timeFilter),
        api.getTopTracks(timeFilter, 5),
        api.getTopArtists(timeFilter, 5),
        api.getRadar(timeFilter),
        api.getHeatmap(timeFilter),
        api.getBarChartRace('1y'),
        api.getGenreDistribution(timeFilter),
        api.getLatestPersona('monthly'),
        api.getListeningHistory(20),
      ]);

      setSummary(sum);
      setTopTracks(tracks);
      setTopArtists(artists);
      setRadarData(radar);
      setHeatmapData(heatmap);
      setRaceData(race);
      setGenreData(genres);
      setPersona(p);
      setRecentScrobbles(history);
    } catch {
      // Graceful fallback da xu ly trong api client
    }
  }, [user]);

  // 2. Kiem tra OAuth Callback & Token khi ung dung khoi tao
  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const authSuccess = params.get('auth_success');
    const authError = params.get('auth_error');

    if (authError) {
      window.history.replaceState({}, document.title, window.location.pathname);
      setTimeout(() => {
        addToast('error', decodeURIComponent(authError));
      }, 0);
    } else if (token) {
      localStorage.setItem('access_token', token);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (authSuccess) {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Kiem tra phien lam viec hien tai - KHONG goi triggerSync o day de tranh block spinner
    api.getCurrentUser()
      .then((currentUser) => {
        if (currentUser) {
          setUser(currentUser);
          setIsDemoMode(false);
          if (token || authSuccess) {
            addToast('success', 'Đăng nhập Spotify thành công! Đang tải hồ sơ của bạn...');
          }
        }
      })
      .catch(() => {
        setUser(null);
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
      setIsLoadingPeriods(true);
      try {
        const periods = await api.getAvailablePeriods(periodType, 12);
        if (!isCancelled && periods.length > 0) {
          setAvailablePeriods(periods);
          setSelectedPeriod((prev) => {
            const match = prev && periods.find((p) => p.key === prev.key);
            return match || periods[0];
          });
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
    } catch {
      addToast('error', 'Lỗi kết nối máy chủ xác thực.');
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
    setPeriodType('week');
    setAvailablePeriods(MOCK_CALENDAR_PERIODS.week);
    setSelectedPeriod(MOCK_CALENDAR_PERIODS.week[0]);
    setSummary(MOCK_SUMMARY);
    setTopTracks(MOCK_TOP_TRACKS);
    setTopArtists(MOCK_TOP_ARTISTS);
    setRadarData(MOCK_RADAR);
    setHeatmapData(MOCK_HEATMAP);
    setRaceData(MOCK_RACE);
    setGenreData(MOCK_GENRES);
    setPersona(MOCK_PERSONA);
    addToast('info', 'Đã bật Chế độ Xem thử (Demo) với dữ liệu mẫu.');
  };

  const handleExitDemo = () => {
    setIsDemoMode(false);
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

    setIsGeneratingPersona(true);
    try {
      const newPersona = await api.generatePersona('monthly');
      setPersona(newPersona);
      addToast('success', 'Đã phân tích và cập nhật AI Persona mới thành công!');
    } catch {
      addToast('error', 'Không thể tạo AI Persona. Vui lòng kiểm tra API Key.');
    } finally {
      setIsGeneratingPersona(false);
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
    try {
      const res = await api.getRecommendations(trackId, 5);
      setRecData(res);
    } catch {
      addToast('error', 'Không thể tìm bài hát tương tự.');
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

          {/* 1. Quick Stats Overview Grid */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <StatCard
              title="Tổng Lượt Nghe"
              value={summary.total_plays.toLocaleString()}
              subtitle={selectedPeriod ? selectedPeriod.label : 'Trong kỳ này'}
              icon={<Headphones className="w-5 h-5" />}
            />
            <StatCard
              title="Thời Lượng Thưởng Thức"
              value={`${summary.total_hours} giờ`}
              subtitle="Thời gian phát trực tiếp"
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
                />
              </section>

              {/* 3. Deep Visual Analytics: Radar & 24x7 Heatmap */}
              <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-5 flex">
                  <RadarChartComponent data={radarData.features} />
                </div>
                <div className="lg:col-span-7 flex">
                  <ListeningHeatmap data={heatmapData.matrix} />
                </div>
              </section>

              {/* 4. Thể Loại Âm Nhạc Chủ Đạo (Top Genres Stream Distribution) */}
              <section>
                <GenreDistribution data={genreData} />
              </section>

              {/* 5. Top Charts: Tracks & Artists */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <TopTracksList tracks={topTracks} onFindSimilar={handleFindSimilarSongs} />
                <TopArtistsList artists={topArtists} />
              </section>

              {/* 7. Animated Bar Chart Race */}
              <section>
                <BarChartRace timeline={raceData.timeline} />
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
        personaTitle={persona.persona_title}
        tagline={persona.tagline}
        topArtists={topArtists.map((a) => a.name)}
        topGenres={genreData.genres.map((g) => g.name)}
        period={selectedPeriod ? selectedPeriod.label : 'Kỳ thống kê'}
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
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
