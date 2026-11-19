import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
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

import type { RecommendationResult } from './types/ai';
import {
  api,
  buildMockRecommendations,
  getDynamicMockCalendarPeriods,
} from './services/api';
import { formatListeningDuration } from './utils/analyticsFormatters';
import { useToast } from './hooks/useToast';
import { useAuthSession } from './hooks/useAuthSession';
import { useDashboardPeriod } from './hooks/useDashboardPeriod';
import { useDashboardData } from './hooks/useDashboardData';
import { useSpotifySync } from './hooks/useSpotifySync';

import { Navbar } from './components/ui/Navbar';
import { LoginHero } from './components/ui/LoginHero';
import { ToastContainer } from './components/ui/Toast';
import { StatCard } from './components/ui/StatCard';
import { CalendarPeriodSelector } from './components/ui/CalendarPeriodSelector';
import { SectionErrorState } from './components/ui/SectionState';

import { RadarChartComponent } from './components/charts/RadarChartComponent';
import { ListeningHeatmap } from './components/charts/ListeningHeatmap';
import { GenreDistribution } from './components/charts/GenreDistribution';
import { WeeklyComparisonChart } from './components/charts/WeeklyComparisonChart';

import { PersonaCard } from './components/cards/PersonaCard';
import { MusicFactsSection } from './components/analytics/MusicFactsSection';
import { CodebaseAssistantSection } from './components/analytics/CodebaseAssistantSection';
import { TopTracksList } from './components/cards/TopTracksList';
import { TopArtistsList } from './components/cards/TopArtistsList';
import { TopAlbumsList } from './components/cards/TopAlbumsList';
import { RecentScrobblesList } from './components/cards/RecentScrobblesList';

const RecommendationModal = lazy(() =>
  import('./components/cards/RecommendationModal').then((m) => ({
    default: m.RecommendationModal,
  })),
);
const ShareableCard = lazy(() =>
  import('./components/cards/ShareableCard').then((m) => ({
    default: m.ShareableCard,
  })),
);

export function App() {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const { toasts, addToast, dismissToast } = useToast();

  const exitDemoOnly = useCallback(() => {
    setIsDemoMode(false);
  }, []);

  const {
    user,
    setUser,
    isCheckingAuth,
    authCheckError,
    isLoggingIn,
    checkSession,
    handleLogin,
    handleLogout: rawLogout,
  } = useAuthSession({
    addToast,
    onDemoModeExit: exitDemoOnly,
  });

  const [periodsError, setPeriodsError] = useState<string | null>(null);
  const handlePeriodsError = useCallback((msg: string) => {
    setPeriodsError(msg);
  }, []);

  const {
    periodType,
    setPeriodType,
    availablePeriods,
    setAvailablePeriods,
    selectedPeriod,
    setSelectedPeriod,
    isLoadingPeriods,
    handlePeriodTypeChange,
    handlePeriodSelect,
  } = useDashboardPeriod({
    user,
    isDemoMode,
    onPeriodsError: handlePeriodsError,
  });

  const handleUnauthorized = useCallback(() => {
    localStorage.removeItem('access_token');
    setUser(null);
    addToast('warning', 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập Spotify lại.');
  }, [setUser, addToast]);

  const {
    summary,
    topTracks,
    topArtists,
    topAlbums,
    radarData,
    heatmapData,
    weeklyComparison,
    genreData,
    recentScrobbles,
    setRecentScrobbles,
    persona,
    setPersona,
    musicFacts,
    setMusicFacts,
    agentMeta,
    setAgentMeta,
    sectionStates,
    analyticsError,
    setAnalyticsError,
    refreshAllData,
    retrySection,
    resetToEmpty,
    populateDemoData,
  } = useDashboardData({
    user,
    isDemoMode,
    periodType,
    selectedPeriod,
    onUnauthorized: handleUnauthorized,
  });

  // Giữ ref chống chạy auto-sync lặp lại khi khởi tạo phiên đăng nhập
  const hasAutoSyncedRef = useRef(false);

  const { isSyncing, handleSync } = useSpotifySync({
    user,
    isDemoMode,
    periodType,
    selectedPeriod,
    hasAutoSyncedRef,
    setAvailablePeriods,
    setSelectedPeriod,
    refreshAllData,
    addToast,
  });

  // Action & Modal States
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isGeneratingPersona, setIsGeneratingPersona] = useState(false);
  const [isLoadingFacts, setIsLoadingFacts] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isRecModalOpen, setIsRecModalOpen] = useState(false);
  const [recData, setRecData] = useState<RecommendationResult | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);
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

  const handleLogout = useCallback(async () => {
    hasAutoSyncedRef.current = false;
    resetToEmpty();
    await rawLogout();
  }, [rawLogout, resetToEmpty]);

  const handleEnterDemo = useCallback(() => {
    setIsDemoMode(true);
    setPeriodsError(null);
    localStorage.setItem('user_calendar_selected_mode', 'current');
    localStorage.removeItem('user_calendar_selected_key');
    const dynamicMocks = getDynamicMockCalendarPeriods();
    setPeriodType('week');
    setAvailablePeriods(dynamicMocks.week);
    setSelectedPeriod(dynamicMocks.week[0]);
    populateDemoData(dynamicMocks.week[0], 'week');
    addToast('info', 'Đã bật Chế độ Xem thử (Demo) với dữ liệu mẫu.');
  }, [setPeriodType, setAvailablePeriods, setSelectedPeriod, populateDemoData, addToast]);

  const handleExitDemo = useCallback(() => {
    setIsDemoMode(false);
    setPeriodsError(null);
    resetToEmpty();
  }, [resetToEmpty]);

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
          addToast(
            'info',
            `Đã phân tích AI Persona thành công qua model dự phòng (${newPersona.model_name || 'Backup'})!`,
          );
        } else {
          addToast('success', 'Đã phân tích và cập nhật AI Persona mới thành công!');
        }
      }
    } catch {
      addToast('error', 'Không thể tạo AI Persona. Vui lòng kiểm tra cấu hình AI.');
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
          addToast(
            'info',
            `Aura Detective Agent đã dùng model dự phòng (${res.agent_meta.model_name || 'Backup'}) để điều tra thành công!`,
          );
        } else if (
          res.agent_meta &&
          !res.agent_meta.is_fallback &&
          res.agent_meta.provider_used !== 'db-analytics-preview'
        ) {
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

  const combinedBannerError = analyticsError || periodsError;
  const isSummaryLoading = Boolean(user && sectionStates.summary.loading);
  const summaryError = user ? sectionStates.summary.error : null;
  const isEmptyPeriod =
    !isSummaryLoading && !summaryError && summary.total_plays === 0;
  const isSummaryFailedWithNoData =
    !isSummaryLoading && Boolean(summaryError) && summary.total_plays === 0;

  const compSummary = weeklyComparison?.summary;
  let playsTrend: string | undefined;
  let playsTrendTone: 'positive' | 'negative' | 'neutral' = 'neutral';
  if (
    !sectionStates.comparison.loading &&
    !sectionStates.comparison.error &&
    summary.total_plays > 0 &&
    compSummary
  ) {
    if (compSummary.baseline_status === 'new_activity') {
      playsTrend = 'Hoạt động mới';
      playsTrendTone = 'positive';
    } else if (compSummary.baseline_status === 'normal' && compSummary.growth_percentage !== null) {
      const g = compSummary.growth_percentage;
      playsTrend = g > 0 ? `+${g}%` : `${g}%`;
      playsTrendTone = g > 0 ? 'positive' : g < 0 ? 'negative' : 'neutral';
    }
  }

  return (
    <div className="min-h-screen bg-obsidian-bg text-text-main flex flex-col">
      <Navbar
        user={user}
        isDemoMode={isDemoMode}
        isSyncing={isSyncing}
        onSync={handleSync}
        onLogout={handleLogout}
        onLogin={handleLogin}
        onExitDemo={handleExitDemo}
      />

      <div className="flex-1 min-w-0">
        {isCheckingAuth ? (
          <div className="min-h-[80vh] flex flex-col items-center justify-center gap-4 px-4">
            <div className="w-10 h-10 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-text-muted font-medium">Đang kiểm tra phiên làm việc...</p>
          </div>
        ) : authCheckError && !user && !isDemoMode ? (
          <div className="min-h-[80vh] flex flex-col items-center justify-center px-4 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="max-w-md space-y-1.5">
              <h2 className="text-lg font-bold text-white">Không thể kết nối máy chủ xác thực</h2>
              <p className="text-xs sm:text-sm text-text-muted">{authCheckError}</p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={checkSession}
                className="min-h-[40px] px-4 py-2 rounded-xl text-xs font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                Thử lại
              </button>
              <button
                type="button"
                onClick={handleEnterDemo}
                className="min-h-[40px] px-4 py-2 rounded-xl text-xs font-semibold bg-obsidian-card border border-obsidian-border text-slate-200 hover:text-white transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
              >
                Xem thử Demo
              </button>
            </div>
          </div>
        ) : !user && !isDemoMode ? (
          <LoginHero
            onLogin={handleLogin}
            onEnterDemo={handleEnterDemo}
            isLoading={isLoggingIn}
          />
        ) : (
          <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-5 sm:py-8 space-y-6 sm:space-y-8 animate-fade-in">
            {/* Demo Mode Notice Banner */}
            {isDemoMode && (
              <div className="p-4 rounded-2xl bg-amber-950/40 border border-amber-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-start sm:items-center gap-3 text-left min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
                    <Radio className="w-4 h-4 animate-pulse" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-amber-200">
                      Bạn đang ở Chế độ Xem thử (Demo Mode)
                    </h2>
                    <p className="text-[11px] sm:text-xs text-amber-200/80 leading-relaxed">
                      Toàn bộ biểu đồ và chỉ số đang phản ánh dữ liệu mẫu. Kết nối tài khoản Spotify của bạn để theo dõi dữ liệu thực tế.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleLogin}
                  className="shrink-0 min-h-[38px] inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all cursor-pointer shadow-md shadow-spotify-green/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                >
                  <span>Đăng nhập Spotify ngay</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Dashboard Header & Calendar Period Filter */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-4 border-b border-obsidian-border gap-4">
              <div className="min-w-0">
                <h1 className="text-xl sm:text-3xl font-black text-white tracking-tight">
                  Bảng Phân Tích Thống Kê Âm Nhạc
                </h1>
                <p className="text-xs sm:text-sm text-text-muted mt-1">
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

            {combinedBannerError && user && (
              <div
                role="alert"
                className="p-4 rounded-2xl bg-rose-950/35 border border-rose-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex items-start sm:items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-rose-100">
                      Một số mục dữ liệu chưa tải được đầy đủ từ máy chủ
                    </h2>
                    <p className="text-[11px] sm:text-xs text-rose-200/80 break-words">
                      {combinedBannerError}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setAnalyticsError(null);
                    setPeriodsError(null);
                    refreshAllData(selectedPeriod, { clearPeriodData: false });
                  }}
                  className="shrink-0 min-h-[38px] inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-rose-500/20 hover:bg-rose-500/30 text-rose-100 border border-rose-500/30 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Tải lại tất cả</span>
                </button>
              </div>
            )}

            {/* 1. Quick Stats Overview Grid */}
            <section aria-label="Chỉ số tổng quan kỳ thống kê" className="grid grid-cols-1 min-[380px]:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
              <StatCard
                title="Lượt phát"
                value={summary.total_plays.toLocaleString()}
                trend={playsTrend}
                trendTone={playsTrendTone}
                subtitle={
                  summary.unique_tracks_count && summary.unique_tracks_count > 0
                    ? `${summary.unique_tracks_count.toLocaleString()} bài hát khác nhau`
                    : selectedPeriod
                    ? selectedPeriod.label
                    : 'Trong kỳ này'
                }
                tooltip="Tổng lượt phát trong kỳ đang chọn (một bài nghe nhiều lần tính nhiều lượt) kèm chênh lệch so với kỳ trước tương đương."
                icon={<Headphones className="w-4 h-4 sm:w-5 sm:h-5" />}
                isLoading={isSummaryLoading}
              />
              <StatCard
                title="Thời lượng nghe ước tính"
                value={formatListeningDuration(summary.total_duration_ms, summary.total_hours)}
                subtitle="Tổng độ dài các bản nhạc đã phát"
                tooltip="Ước tính từ thời lượng chuẩn của mỗi bản nhạc đã phát trong kỳ."
                icon={<Clock className="w-4 h-4 sm:w-5 sm:h-5" />}
                isLoading={isSummaryLoading}
              />
              <StatCard
                title="Nghệ sĩ"
                value={summary.unique_artists_count.toLocaleString()}
                subtitle="Nghệ sĩ độc nhất trong kỳ"
                icon={<Mic2 className="w-4 h-4 sm:w-5 sm:h-5" />}
                isLoading={isSummaryLoading}
              />
              <StatCard
                title="Album"
                value={summary.unique_albums_count.toLocaleString()}
                subtitle="Album / Đĩa đơn độc nhất"
                icon={<Disc className="w-4 h-4 sm:w-5 sm:h-5" />}
                isLoading={isSummaryLoading}
              />
            </section>

            {/* Phân biệt rạch ròi Lỗi tải kỳ thống kê vs Kỳ không có lượt nghe */}
            {isSummaryFailedWithNoData ? (
              <section>
                <SectionErrorState
                  title="Không thể tải dữ liệu cho kỳ thống kê này"
                  message={summaryError || 'Đã xảy ra lỗi kết nối khi tải số liệu.'}
                  onRetry={() => refreshAllData(selectedPeriod, { clearPeriodData: false })}
                />
              </section>
            ) : isEmptyPeriod ? (
              <section className="p-6 sm:p-12 rounded-2xl bg-obsidian-card border border-obsidian-border text-center flex flex-col items-center justify-center space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400">
                  <CalendarOff className="w-7 h-7" />
                </div>
                <div className="max-w-md space-y-2">
                  <h3 className="text-base sm:text-lg font-bold text-white">
                    Bạn chưa có dữ liệu nghe trong khoảng thời gian này
                  </h3>
                  <p className="text-xs sm:text-sm text-text-muted leading-relaxed">
                    Spotify chưa ghi nhận lượt nghe nào của bạn trong {selectedPeriod?.label || 'kỳ thống kê này'}. Hãy chọn một khoảng thời gian khác hoặc quay lại kỳ hiện tại để xem phân tích chi tiết.
                  </p>
                </div>
                {availablePeriods.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      const current = availablePeriods.find((p) => p.is_current) || availablePeriods[0];
                      if (current) handlePeriodSelect(current);
                    }}
                    className="mt-2 min-h-[40px] inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-spotify-green text-black hover:bg-spotify-hover transition-all cursor-pointer shadow-md shadow-spotify-green/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Quay lại kỳ hiện tại</span>
                  </button>
                )}
              </section>
            ) : (
              <>
                {/* 2. Xu hướng Nghe nhạc Thích ứng (Tuần / Tháng / Năm) */}
                <section>
                  <WeeklyComparisonChart
                    data={weeklyComparison}
                    periodType={periodType}
                    isLoading={sectionStates.comparison.loading}
                    error={sectionStates.comparison.error}
                    onRetry={() => retrySection('comparison')}
                  />
                </section>

                {/* 3. Bản đồ Nhiệt Hoạt động Nghe nhạc */}
                <section>
                  <ListeningHeatmap
                    data={heatmapData.matrix}
                    periodType={periodType}
                    monthCalendar={heatmapData.month_calendar}
                    yearCalendar={heatmapData.year_calendar}
                    selectedPeriodLabel={selectedPeriod?.label}
                    isLoading={sectionStates.heatmap.loading}
                    error={sectionStates.heatmap.error}
                    onRetry={() => retrySection('heatmap')}
                  />
                </section>

                {/* 4. Khẩu vị Âm nhạc: Radar 5D & Phân bố Thể loại */}
                <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                  <div className="lg:col-span-5 flex min-w-0">
                    <RadarChartComponent
                      data={radarData.features}
                      totalTracksAnalyzed={radarData.total_tracks_analyzed}
                      provenance={radarData.provenance}
                      isLoading={sectionStates.radar.loading}
                      error={sectionStates.radar.error}
                      onRetry={() => retrySection('radar')}
                    />
                  </div>
                  <div className="lg:col-span-7 flex min-w-0">
                    <GenreDistribution
                      data={genreData}
                      isLoading={sectionStates.genres.loading}
                      error={sectionStates.genres.error}
                      onRetry={() => retrySection('genres')}
                    />
                  </div>
                </section>

                {/* 5. Bảng xếp hạng: Top Bài hát, Top Nghệ sĩ & Top Album */}
                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <TopTracksList
                    tracks={topTracks}
                    onFindSimilar={handleFindSimilarSongs}
                    periodLabel={selectedPeriod?.label}
                    isLoading={sectionStates.topTracks.loading}
                    error={sectionStates.topTracks.error}
                    onRetry={() => retrySection('topTracks')}
                  />
                  <TopArtistsList
                    artists={topArtists}
                    periodLabel={selectedPeriod?.label}
                    isLoading={sectionStates.topArtists.loading}
                    error={sectionStates.topArtists.error}
                    onRetry={() => retrySection('topArtists')}
                  />
                  <TopAlbumsList
                    albums={topAlbums}
                    periodLabel={selectedPeriod?.label}
                    isLoading={sectionStates.topAlbums.loading}
                    error={sectionStates.topAlbums.error}
                    onRetry={() => retrySection('topAlbums')}
                    className="md:col-span-2 lg:col-span-1"
                  />
                </section>

                {/* 6. Khám phá AI: AI Music Persona & AI Music Detective */}
                <section>
                  <PersonaCard
                    persona={persona}
                    isLoading={sectionStates.persona.loading}
                    isGenerating={isGeneratingPersona}
                    error={sectionStates.persona.error}
                    onRegenerate={handleRegeneratePersona}
                    onRetry={() => retrySection('persona')}
                    onOpenShareModal={() => setIsShareModalOpen(true)}
                    cooldownSeconds={personaCooldown}
                  />
                </section>

                <section>
                  <MusicFactsSection
                    facts={musicFacts}
                    agentMeta={agentMeta}
                    periodLabel={selectedPeriod ? selectedPeriod.label : 'Tuần này'}
                    isLoading={isLoadingFacts || sectionStates.facts.loading}
                    error={sectionStates.facts.error}
                    onRefresh={handleRefreshFacts}
                    onRetry={() => retrySection('facts')}
                    cooldownSeconds={factsCooldown}
                  />
                </section>
              </>
            )}

            {/* 8. Nhật Ký Nghe Nhạc Gần Đây (Recent Scrobbles) */}
            <section>
              <RecentScrobblesList
                records={recentScrobbles}
                isLoading={isLoadingHistory || sectionStates.history.loading}
                error={sectionStates.history.error}
                onRefresh={handleRefreshHistory}
                onRetry={() => retrySection('history')}
                onFindSimilar={handleFindSimilarSongs}
              />
            </section>

            {/* 9. Trợ lý Hỗ trợ Người dùng ở vị trí cố định cuối Dashboard */}
            <section>
              <CodebaseAssistantSection
                key={isDemoMode ? 'demo-assistant' : `auth-assistant-${user?.id ?? 'anon'}`}
                onAddToast={addToast}
                isAdmin={Boolean(user?.is_staff)}
                selectedPeriod={selectedPeriod}
                periodType={periodType}
                isDemoMode={isDemoMode}
              />
            </section>
          </main>
        )}
      </div>

      {/* Footer gọn gàng hướng tới người dùng */}
      <footer className="w-full bg-obsidian-bg border-t border-obsidian-border mt-12 sm:mt-16 py-6 sm:py-8">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-text-muted gap-3 text-center sm:text-left">
          <p>MusicTrack - Nhật ký & Phân tích Thói quen Nghe nhạc Spotify</p>
          <p>Dữ liệu được đồng bộ bảo mật và hiển thị theo múi giờ của bạn</p>
        </div>
      </footer>

      {/* Modal Xuất Thẻ Chia Sẻ (Lazy loaded) */}
      {isShareModalOpen && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm">
              <div className="w-8 h-8 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
            </div>
          }
        >
          <ShareableCard
            userName={user?.display_name || user?.username || 'Thính giả Demo'}
            avatarUrl={user?.profile_image_url || undefined}
            personaTitle={persona?.persona_title || 'Người Khám Phá Âm Nhạc'}
            tagline={persona?.tagline || 'Âm nhạc phản chiếu tâm hồn và nhịp sống của riêng bạn.'}
            topArtists={topArtists.map((a) => a.name)}
            topGenres={genreData.genres.map((g) => g.name)}
            period={selectedPeriod ? selectedPeriod.label : 'Kỳ thống kê'}
            periodType={periodType}
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
        </Suspense>
      )}

      {/* Modal Gợi Ý Bài Hát Tương Đồng (Lazy loaded) */}
      {isRecModalOpen && (
        <Suspense
          fallback={
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm">
              <div className="w-8 h-8 border-2 border-spotify-green border-t-transparent rounded-full animate-spin" />
            </div>
          }
        >
          <RecommendationModal
            isOpen={isRecModalOpen}
            onClose={() => setIsRecModalOpen(false)}
            data={recData}
            isLoading={isLoadingRecs}
          />
        </Suspense>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default App;
