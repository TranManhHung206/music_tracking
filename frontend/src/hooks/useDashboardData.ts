import { useState, useCallback, useEffect, useRef } from 'react';
import type { UserProfile } from '../types/auth';
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
} from '../types/analytics';
import type { AIMusicPersona, MusicFact, AgentMeta } from '../types/ai';
import { isValidPersona } from '../types/ai';
import {
  api,
  ApiError,
  isRequestCanceled,
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
} from '../services/api';
import {
  ALL_SECTIONS,
  EMPTY_GENRES,
  EMPTY_HEATMAP,
  EMPTY_RADAR,
  EMPTY_SUMMARY,
  EMPTY_WEEKLY_COMPARISON,
  PERIOD_SCOPED_SECTIONS,
  createSectionStatusMap,
  isStaleDashboardResponse,
  resolveTimeFilterForPeriod,
  type SectionKey,
  type SectionStatusMap,
} from './dashboardDataState';

interface UseDashboardDataOptions {
  user: UserProfile | null;
  isDemoMode: boolean;
  periodType: CalendarPeriodType;
  selectedPeriod: CalendarPeriodItem | null;
  onUnauthorized: () => void;
}

/** Điều phối tải dữ liệu từng khu vực kèm AbortController chống race condition và cô lập lỗi cục bộ. */
export function useDashboardData({
  user,
  isDemoMode,
  periodType,
  selectedPeriod,
  onUnauthorized,
}: UseDashboardDataOptions) {
  const [summary, setSummary] = useState<SummaryStats>(EMPTY_SUMMARY);
  const [topTracks, setTopTracks] = useState<TopTrack[]>([]);
  const [topArtists, setTopArtists] = useState<TopArtist[]>([]);
  const [topAlbums, setTopAlbums] = useState<TopAlbum[]>([]);
  const [radarData, setRadarData] = useState<RadarData>(EMPTY_RADAR);
  const [heatmapData, setHeatmapData] = useState<HeatmapData>(EMPTY_HEATMAP);
  const [weeklyComparison, setWeeklyComparison] = useState<WeeklyComparisonData>(EMPTY_WEEKLY_COMPARISON);
  const [genreData, setGenreData] = useState<GenreDistributionData>(EMPTY_GENRES);
  const [recentScrobbles, setRecentScrobbles] = useState<ListeningHistoryRecord[]>([]);
  const [persona, setPersona] = useState<AIMusicPersona | null>(null);
  const [musicFacts, setMusicFacts] = useState<MusicFact[]>([]);
  const [agentMeta, setAgentMeta] = useState<AgentMeta | undefined>(undefined);

  const [sectionStates, setSectionStates] = useState<SectionStatusMap>(() => createSectionStatusMap());
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  const requestIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastScopeKeyRef = useRef<string>('');

  const resetToEmpty = useCallback(() => {
    abortControllerRef.current?.abort();
    requestIdRef.current += 1;
    lastScopeKeyRef.current = '';
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
    setSectionStates(createSectionStatusMap());
    setAnalyticsError(null);
  }, []);

  const populateDemoData = useCallback(() => {
    abortControllerRef.current?.abort();
    requestIdRef.current += 1;
    setAnalyticsError(null);
    setSectionStates(createSectionStatusMap());
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
  }, []);

  const setSectionStatus = useCallback((key: SectionKey, loading: boolean, error: string | null) => {
    setSectionStates((prev) => ({
      ...prev,
      [key]: { loading, error },
    }));
  }, []);

  const refreshAllData = useCallback(
    async (period: CalendarPeriodItem | null, options?: { clearPeriodData?: boolean }) => {
      if (!user) {
        if (isDemoMode) {
          setHeatmapData((prev) => ({ ...prev, period_type: periodType }));
        }
        return;
      }

      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const currentReqId = ++requestIdRef.current;

      const scopeKey = `${periodType}:${period?.key || 'default'}`;
      const periodChanged = options?.clearPeriodData ?? (lastScopeKeyRef.current !== '' && lastScopeKeyRef.current !== scopeKey);
      lastScopeKeyRef.current = scopeKey;

      setAnalyticsError(null);

      if (periodChanged) {
        setSummary(EMPTY_SUMMARY);
        setTopTracks([]);
        setTopArtists([]);
        setTopAlbums([]);
        setRadarData(EMPTY_RADAR);
        setHeatmapData({ ...EMPTY_HEATMAP, period_type: periodType });
        setWeeklyComparison({ ...EMPTY_WEEKLY_COMPARISON, period_type: periodType });
        setGenreData(EMPTY_GENRES);
        setMusicFacts([]);
        setAgentMeta(undefined);
      }

      const loadingTargets = periodChanged ? PERIOD_SCOPED_SECTIONS : ALL_SECTIONS;
      setSectionStates((prev) => {
        const next = { ...prev };
        for (const k of loadingTargets) {
          next[k] = { loading: true, error: null };
        }
        return next;
      });

      const timeFilter = resolveTimeFilterForPeriod(period, periodType);
      const sig = controller.signal;

      const results = await Promise.allSettled([
        api.getSummary(timeFilter, sig),
        api.getTopTracks(timeFilter, 5, sig),
        api.getTopArtists(timeFilter, 5, sig),
        api.getTopAlbums(timeFilter, 5, sig),
        api.getRadar(timeFilter, sig),
        api.getHeatmap(timeFilter, periodType, sig),
        api.getWeeklyComparison(timeFilter, periodType, sig),
        api.getGenreDistribution(timeFilter, sig),
        api.getLatestPersona('monthly', sig),
        api.getListeningHistory(20, sig),
        api.getMusicFacts(period?.key || 'week', false, false, sig),
      ]);

      if (isStaleDashboardResponse({ activeRequestId: requestIdRef.current, requestId: currentReqId, aborted: sig.aborted })) {
        return;
      }

      const keys: SectionKey[] = [
        'summary',
        'topTracks',
        'topArtists',
        'topAlbums',
        'radar',
        'heatmap',
        'comparison',
        'genres',
        'persona',
        'history',
        'facts',
      ];

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

      let hasUnauthorized = false;
      let firstNonCancelMsg: string | null = null;
      const updates: Partial<SectionStatusMap> = {};

      results.forEach((res, index) => {
        const key = keys[index];
        if (res.status === 'fulfilled') {
          updates[key] = { loading: false, error: null };
        } else if (isRequestCanceled(res.reason)) {
          updates[key] = { loading: false, error: null };
        } else {
          if (res.reason instanceof ApiError && res.reason.status === 401) {
            hasUnauthorized = true;
          }
          const errMsg =
            res.reason instanceof Error
              ? res.reason.message
              : 'Không thể tải dữ liệu mục này.';
          if (!firstNonCancelMsg) firstNonCancelMsg = errMsg;
          updates[key] = { loading: false, error: errMsg };
        }
      });

      if (hasUnauthorized) {
        onUnauthorized();
        return;
      }

      setSectionStates((prev) => ({ ...prev, ...updates }));
      if (firstNonCancelMsg) {
        setAnalyticsError(firstNonCancelMsg);
      }
    },
    [user, isDemoMode, periodType, onUnauthorized]
  );

  const retrySection = useCallback(
    async (key: SectionKey) => {
      if (!user) return;
      const activeReqId = requestIdRef.current;
      const timeFilter = resolveTimeFilterForPeriod(selectedPeriod, periodType);
      setSectionStatus(key, true, null);

      try {
        switch (key) {
          case 'summary':
            setSummary(await api.getSummary(timeFilter));
            break;
          case 'topTracks':
            setTopTracks(await api.getTopTracks(timeFilter, 5));
            break;
          case 'topArtists':
            setTopArtists(await api.getTopArtists(timeFilter, 5));
            break;
          case 'topAlbums':
            setTopAlbums(await api.getTopAlbums(timeFilter, 5));
            break;
          case 'radar':
            setRadarData(await api.getRadar(timeFilter));
            break;
          case 'heatmap':
            setHeatmapData(await api.getHeatmap(timeFilter, periodType));
            break;
          case 'comparison':
            setWeeklyComparison(await api.getWeeklyComparison(timeFilter, periodType));
            break;
          case 'genres':
            setGenreData(await api.getGenreDistribution(timeFilter));
            break;
          case 'persona': {
            const p = await api.getLatestPersona('monthly');
            setPersona(isValidPersona(p) ? p : null);
            break;
          }
          case 'history':
            setRecentScrobbles(await api.getListeningHistory(20));
            break;
          case 'facts': {
            const res = await api.getMusicFacts(selectedPeriod?.key || 'week', false, false);
            if (res && Array.isArray(res.facts)) {
              setMusicFacts(res.facts);
              setAgentMeta(res.agent_meta);
            }
            break;
          }
        }
        if (requestIdRef.current === activeReqId) {
          setSectionStatus(key, false, null);
        }
      } catch (err) {
        if (isRequestCanceled(err)) return;
        if (err instanceof ApiError && err.status === 401) {
          onUnauthorized();
          return;
        }
        const msg = err instanceof Error ? err.message : 'Thử lại không thành công.';
        if (requestIdRef.current === activeReqId) {
          setSectionStatus(key, false, msg);
        }
      }
    },
    [user, selectedPeriod, periodType, setSectionStatus, onUnauthorized]
  );

  useEffect(() => {
    if (!user || !selectedPeriod) return;
    let isCancelled = false;
    Promise.resolve().then(() => {
      if (!isCancelled) {
        void refreshAllData(selectedPeriod);
      }
    });
    return () => {
      isCancelled = true;
      abortControllerRef.current?.abort();
    };
  }, [user, selectedPeriod, refreshAllData]);

  return {
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
  };
}
