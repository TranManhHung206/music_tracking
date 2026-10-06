import { useState, useEffect, useCallback } from 'react';
import {
  Headphones,
  Clock,
  Mic2,
  Disc,
} from 'lucide-react';

import type { UserProfile } from './types/auth';
import type {
  TimeRange,
  SummaryStats,
  TopTrack,
  TopArtist,
  RadarData,
  HeatmapData,
  BarChartRaceData,
} from './types/analytics';
import type { AIMusicPersona, RecommendationResult } from './types/ai';

import {
  api,
  MOCK_USER,
  MOCK_SUMMARY,
  MOCK_TOP_TRACKS,
  MOCK_TOP_ARTISTS,
  MOCK_RADAR,
  MOCK_HEATMAP,
  MOCK_RACE,
  MOCK_PERSONA,
} from './services/api';

import { Navbar } from './components/ui/Navbar';
import { StatCard } from './components/ui/StatCard';
import { TimeRangeSelector } from './components/ui/TimeRangeSelector';

import { RadarChartComponent } from './components/charts/RadarChartComponent';
import { ListeningHeatmap } from './components/charts/ListeningHeatmap';
import { BarChartRace } from './components/charts/BarChartRace';

import { PersonaCard } from './components/cards/PersonaCard';
import { TopTracksList } from './components/cards/TopTracksList';
import { TopArtistsList } from './components/cards/TopArtistsList';
import { RecommendationModal } from './components/cards/RecommendationModal';
import { ShareableCard } from './components/cards/ShareableCard';

export function App() {
  // Authentication & User State
  const [user, setUser] = useState<UserProfile | null>(MOCK_USER);

  // Time Filter State
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Analytics Data State
  const [summary, setSummary] = useState<SummaryStats>(MOCK_SUMMARY);
  const [topTracks, setTopTracks] = useState<TopTrack[]>(MOCK_TOP_TRACKS);
  const [topArtists, setTopArtists] = useState<TopArtist[]>(MOCK_TOP_ARTISTS);
  const [radarData, setRadarData] = useState<RadarData>(MOCK_RADAR);
  const [heatmapData, setHeatmapData] = useState<HeatmapData>(MOCK_HEATMAP);
  const [raceData, setRaceData] = useState<BarChartRaceData>(MOCK_RACE);

  // AI Persona & Recommendations State
  const [persona, setPersona] = useState<AIMusicPersona>(MOCK_PERSONA);
  const [isGeneratingPersona, setIsGeneratingPersona] = useState(false);

  // Modals & Action States
  const [isSyncing, setIsSyncing] = useState(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [isRecModalOpen, setIsRecModalOpen] = useState(false);
  const [recData, setRecData] = useState<RecommendationResult | null>(null);
  const [isLoadingRecs, setIsLoadingRecs] = useState(false);

  // 1. Kiem tra OAuth Callback tu URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    if (token) {
      localStorage.setItem('access_token', token);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // 2. Fetch User & Analytics Data
  const refreshAllData = useCallback(async (range: TimeRange) => {
    try {
      const [u, sum, tracks, artists, radar, heatmap, race, p] = await Promise.all([
        api.getCurrentUser(),
        api.getSummary(range),
        api.getTopTracks(range, 5),
        api.getTopArtists(range, 5),
        api.getRadar(range),
        api.getHeatmap(range),
        api.getBarChartRace('1y'),
        api.getLatestPersona('monthly'),
      ]);

      if (u) setUser(u);
      setSummary(sum);
      setTopTracks(tracks);
      setTopArtists(artists);
      setRadarData(radar);
      setHeatmapData(heatmap);
      setRaceData(race);
      setPersona(p);
    } catch {
      // Fallback da duoc tich hop trong api service
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;
    const fetchData = async () => {
      try {
        const [u, sum, tracks, artists, radar, heatmap, race, p] = await Promise.all([
          api.getCurrentUser(),
          api.getSummary(timeRange),
          api.getTopTracks(timeRange, 5),
          api.getTopArtists(timeRange, 5),
          api.getRadar(timeRange),
          api.getHeatmap(timeRange),
          api.getBarChartRace('1y'),
          api.getLatestPersona('monthly'),
        ]);

        if (!isCancelled) {
          if (u) setUser(u);
          setSummary(sum);
          setTopTracks(tracks);
          setTopArtists(artists);
          setRadarData(radar);
          setHeatmapData(heatmap);
          setRaceData(race);
          setPersona(p);
        }
      } catch {
        // Fallback da duoc tich hop trong api service
      }
    };

    fetchData();
    return () => {
      isCancelled = true;
    };
  }, [timeRange]);

  // Handlers
  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await api.triggerSync();
      await refreshAllData(timeRange);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRegeneratePersona = async () => {
    setIsGeneratingPersona(true);
    try {
      const newPersona = await api.generatePersona('monthly');
      setPersona(newPersona);
    } finally {
      setIsGeneratingPersona(false);
    }
  };

  const handleFindSimilarSongs = async (trackId: string) => {
    setIsRecModalOpen(true);
    setIsLoadingRecs(true);
    try {
      const res = await api.getRecommendations(trackId, 5);
      setRecData(res);
    } finally {
      setIsLoadingRecs(false);
    }
  };

  const handleLogin = async () => {
    const authUrl = await api.getLoginUrl();
    if (authUrl && authUrl !== '#') {
      window.location.href = authUrl;
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-[#F8FAFC]">
      {/* Top Navbar */}
      <Navbar
        user={user}
        isSyncing={isSyncing}
        onSync={handleSync}
        onLogout={handleLogout}
        onLogin={handleLogin}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Dashboard Header & Time Range Filter */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#1E293B] gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Bảng Phân Tích Thống Kê Âm Nhạc
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Theo dõi thói quen nghe nhạc, các chỉ số Audio Features và cá tính AI Persona
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs text-slate-400 font-medium hidden md:inline">
              Khung thời gian:
            </span>
            <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
          </div>
        </div>

        {/* 1. Quick Stats Overview Grid */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <StatCard
            title="Tổng Lượt Nghe"
            value={summary.total_plays.toLocaleString()}
            subtitle={`Trong ${timeRange}`}
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

        {/* 4. Top Charts: Tracks & Artists */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TopTracksList tracks={topTracks} onFindSimilar={handleFindSimilarSongs} />
          <TopArtistsList artists={topArtists} />
        </section>

        {/* 5. Animated Bar Chart Race */}
        <section>
          <BarChartRace timeline={raceData.timeline} />
        </section>
      </main>

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
        userName={user?.display_name || user?.username || 'Thính giả'}
        avatarUrl={user?.profile_image_url || undefined}
        personaTitle={persona.persona_title}
        tagline={persona.tagline}
        topArtists={topArtists.map((a) => a.name)}
        period={`Kỳ ${timeRange}`}
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
    </div>
  );
}

export default App;
