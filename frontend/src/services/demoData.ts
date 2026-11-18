import type {
  CalendarPeriodItem,
  CalendarPeriodType,
  GenreDistributionData,
  HeatmapCell,
  HeatmapData,
  MonthHeatmapData,
  MonthHeatmapDay,
  RadarData,
  SummaryStats,
  TopAlbum,
  TopArtist,
  TopTrack,
  WeeklyComparisonData,
  YearHeatmapData,
  YearHeatmapDay,
} from '../types/analytics';
import type { AgentMeta, MusicFact } from '../types/ai';

export interface DemoPeriodBundle {
  summary: SummaryStats;
  topTracks: TopTrack[];
  topArtists: TopArtist[];
  topAlbums: TopAlbum[];
  radarData: RadarData;
  heatmapData: HeatmapData;
  weeklyComparison: WeeklyComparisonData;
  genreData: GenreDistributionData;
  musicFacts: MusicFact[];
  agentMeta: AgentMeta;
}

const DEMO_TRACK_BASE: TopTrack[] = [
  {
    spotify_id: 'mock_1',
    name: 'Chúng Ta Của Tương Lai',
    album_name: 'Chúng Ta',
    album_image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
    artists: ['Sơn Tùng M-TP'],
    play_count: 34,
  },
  {
    spotify_id: 'mock_2',
    name: 'Nấu Ăn Cho Em',
    album_name: 'Nấu Ăn Cho Em',
    album_image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    artists: ['Đen Vâu', 'PiaLinh'],
    play_count: 26,
  },
  {
    spotify_id: 'mock_3',
    name: 'Từng Là',
    album_name: 'Từng Là',
    album_image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    artists: ['Vũ Cát Tường'],
    play_count: 21,
  },
  {
    spotify_id: 'mock_4',
    name: 'Blinding Lights',
    album_name: 'After Hours',
    album_image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    artists: ['The Weeknd'],
    play_count: 18,
  },
  {
    spotify_id: 'mock_5',
    name: 'Levitating',
    album_name: 'Future Nostalgia',
    album_image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    artists: ['Dua Lipa'],
    play_count: 16,
  },
];

const DEMO_ARTIST_BASE: TopArtist[] = [
  {
    spotify_id: 'art_1',
    name: 'Sơn Tùng M-TP',
    image_url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&h=300&fit=crop',
    play_count: 62,
  },
  {
    spotify_id: 'art_2',
    name: 'Đen Vâu',
    image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    play_count: 48,
  },
  {
    spotify_id: 'art_3',
    name: 'The Weeknd',
    image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    play_count: 39,
  },
  {
    spotify_id: 'art_4',
    name: 'Vũ Cát Tường',
    image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    play_count: 31,
  },
  {
    spotify_id: 'art_5',
    name: 'Dua Lipa',
    image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    play_count: 27,
  },
];

const DEMO_ALBUM_BASE: TopAlbum[] = [
  {
    spotify_id: 'alb_1',
    name: 'Chúng Ta',
    image_url: 'https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=300&h=300&fit=crop',
    release_date: '2021',
    artists: ['Sơn Tùng M-TP'],
    play_count: 42,
  },
  {
    spotify_id: 'alb_2',
    name: 'Show Của Đen',
    image_url: 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=300&h=300&fit=crop',
    release_date: '2023',
    artists: ['Đen Vâu'],
    play_count: 34,
  },
  {
    spotify_id: 'alb_3',
    name: 'After Hours',
    image_url: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&h=300&fit=crop',
    release_date: '2020',
    artists: ['The Weeknd'],
    play_count: 29,
  },
  {
    spotify_id: 'alb_4',
    name: 'Inner Me',
    image_url: 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=300&h=300&fit=crop',
    release_date: '2019',
    artists: ['Vũ Cát Tường'],
    play_count: 24,
  },
  {
    spotify_id: 'alb_5',
    name: 'Future Nostalgia',
    image_url: 'https://images.unsplash.com/photo-1459749411175-04bf5292ceea?w=300&h=300&fit=crop',
    release_date: '2020',
    artists: ['Dua Lipa'],
    play_count: 20,
  },
];

function buildDeterministicWeekMatrix(targetTotal: number): HeatmapCell[] {
  const cells: HeatmapCell[] = [];
  if (targetTotal <= 0) return cells;

  let rawSum = 0;
  const raw: { day: number; hour: number; val: number }[] = [];
  for (let d = 1; d <= 7; d++) {
    for (let h = 0; h < 24; h++) {
      let val = 0;
      if (h >= 20 && h <= 23) val = ((d * 3 + h) % 6) + 2;
      else if (h >= 9 && h <= 17) val = (d + h) % 4;
      else if (h >= 0 && h <= 1) val = (d + h) % 3;
      raw.push({ day: d, hour: h, val });
      rawSum += val;
    }
  }

  const scale = rawSum > 0 ? targetTotal / rawSum : 1;
  let running = 0;
  for (let i = 0; i < raw.length; i++) {
    const count = i === raw.length - 1 ? Math.max(0, targetTotal - running) : Math.round(raw[i].val * scale);
    running += count;
    cells.push({ day_of_week: raw[i].day, hour: raw[i].hour, count });
  }
  return cells;
}

function buildDeterministicMonthCalendar(key: string, targetTotal: number): MonthHeatmapData {
  const [yStr, mStr] = key.split('-');
  const year = Number(yStr) || new Date().getFullYear();
  const month = Number(mStr) || new Date().getMonth() + 1;
  const totalDays = new Date(year, month, 0).getDate();
  const firstJsDay = new Date(year, month - 1, 1).getDay();
  const firstWeekday = firstJsDay === 0 ? 7 : firstJsDay;

  const weights = Array.from({ length: totalDays }, (_, idx) => {
    const wd = ((firstWeekday - 1 + idx) % 7) + 1;
    return wd >= 5 ? 4 + (idx % 3) : 1 + ((idx * 3) % 4);
  });
  const sumW = weights.reduce((a, b) => a + b, 0);

  let assigned = 0;
  let peakDay = `${year}-${String(month).padStart(2, '0')}-01`;
  let peakPlays = 0;
  let activeDays = 0;

  const days: MonthHeatmapDay[] = weights.map((w, idx) => {
    const dayNumber = idx + 1;
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(dayNumber).padStart(2, '0')}`;
    const wd = ((firstWeekday - 1 + idx) % 7) + 1;
    const count =
      targetTotal <= 0
        ? 0
        : idx === totalDays - 1
        ? Math.max(0, targetTotal - assigned)
        : Math.round((w / sumW) * targetTotal);
    assigned += count;
    if (count > 0) activeDays += 1;
    if (count > peakPlays) {
      peakPlays = count;
      peakDay = dateStr;
    }
    return {
      date: dateStr,
      day_number: dayNumber,
      day_of_week: wd,
      count,
      is_current_month: true,
    };
  });

  return {
    year,
    month,
    first_day_weekday: firstWeekday,
    total_days: totalDays,
    total_plays: targetTotal,
    peak_day: peakDay,
    peak_plays: peakPlays,
    active_days: activeDays,
    max_density: Math.max(peakPlays, 1),
    days,
  };
}

function buildDeterministicYearCalendar(key: string, targetTotal: number): YearHeatmapData {
  const year = Number(key) || new Date().getFullYear();
  const totalWeeks = 53;
  const totalCells = totalWeeks * 7;
  const weights = Array.from({ length: totalCells }, (_, idx) => {
    if (idx % 11 === 0) return 0;
    return ((idx * 5 + 3) % 8) + 1;
  });
  const sumW = weights.reduce((a, b) => a + b, 0);

  let assigned = 0;
  let activeDays = 0;
  let peakDay = `${year}-06-15`;
  let peakPlays = 0;

  const days: YearHeatmapDay[] = weights.map((w, idx) => {
    const weekIndex = Math.floor(idx / 7);
    const dayOfWeek = (idx % 7) + 1;
    const month = Math.min(12, Math.floor(weekIndex / 4.4) + 1);
    const dayNum = (idx % 28) + 1;
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
    const count =
      targetTotal <= 0
        ? 0
        : idx === totalCells - 1
        ? Math.max(0, targetTotal - assigned)
        : Math.floor((w / sumW) * targetTotal);
    assigned += count;
    if (count > 0) activeDays += 1;
    if (count > peakPlays) {
      peakPlays = count;
      peakDay = dateStr;
    }
    return {
      date: dateStr,
      month,
      day_number: dayNum,
      day_of_week: dayOfWeek,
      week_index: weekIndex,
      count,
      is_in_range: true,
    };
  });

  const monthTotals = new Array<number>(12).fill(0);
  days.forEach((d) => {
    monthTotals[d.month - 1] += d.count;
  });
  let topMonth = 1;
  let topMonthPlays = 0;
  monthTotals.forEach((val, idx) => {
    if (val > topMonthPlays) {
      topMonthPlays = val;
      topMonth = idx + 1;
    }
  });

  return {
    year,
    total_weeks: totalWeeks,
    total_days: totalCells,
    total_plays: targetTotal,
    peak_day: peakDay,
    peak_plays: peakPlays,
    active_days: activeDays,
    longest_streak: targetTotal > 0 ? 18 : 0,
    top_month: topMonth,
    top_month_plays: topMonthPlays,
    max_density: Math.max(peakPlays, 1),
    months_header: [
      { month: 1, label: 'T1', start_week: 0 },
      { month: 2, label: 'T2', start_week: 4 },
      { month: 3, label: 'T3', start_week: 8 },
      { month: 4, label: 'T4', start_week: 13 },
      { month: 5, label: 'T5', start_week: 17 },
      { month: 6, label: 'T6', start_week: 22 },
      { month: 7, label: 'T7', start_week: 26 },
      { month: 8, label: 'T8', start_week: 30 },
      { month: 9, label: 'T9', start_week: 35 },
      { month: 10, label: 'T10', start_week: 39 },
      { month: 11, label: 'T11', start_week: 44 },
      { month: 12, label: 'T12', start_week: 48 },
    ],
    days,
  };
}

function scaleGenreDistribution(totalPlays: number, isHistorical: boolean): GenreDistributionData {
  if (totalPlays <= 0) {
    return { genres: [], total_plays: 0, top_genre: 'Chưa có dữ liệu' };
  }

  const ratios = isHistorical
    ? [
        { name: 'V-Pop', pct: 39.0, color: '#EC4899' },
        { name: 'EDM / Electronic', pct: 28.0, color: '#1DB954' },
        { name: 'Global Pop', pct: 18.0, color: '#06B6D4' },
        { name: 'US-UK / Pop', pct: 9.5, color: '#3B82F6' },
        { name: 'Acoustic / Lo-Fi', pct: 5.5, color: '#10B981' },
      ]
    : [
        { name: 'EDM / Electronic', pct: 43.2, color: '#1DB954' },
        { name: 'Global Pop', pct: 28.0, color: '#06B6D4' },
        { name: 'V-Pop', pct: 15.9, color: '#EC4899' },
        { name: 'US-UK / Pop', pct: 8.2, color: '#3B82F6' },
        { name: 'Acoustic / Lo-Fi', pct: 4.7, color: '#10B981' },
      ];

  let used = 0;
  const genres = ratios.map((r, idx) => {
    const plays =
      idx === ratios.length - 1
        ? Math.max(1, totalPlays - used)
        : Math.max(1, Math.round((r.pct / 100) * totalPlays));
    used += plays;
    return {
      name: r.name,
      plays,
      percentage: r.pct,
      color: r.color,
    };
  });

  return {
    genres,
    total_plays: totalPlays,
    top_genre: genres[0].name,
  };
}

function buildComparisonForDemo(
  periodType: CalendarPeriodType,
  currentLabel: string,
  totalPlays: number,
  isCurrent: boolean
): WeeklyComparisonData {
  if (totalPlays <= 0) {
    return {
      time_range: periodType,
      period_type: periodType,
      granularity: periodType === 'year' ? 'month' : periodType === 'month' ? 'week_of_month' : 'day',
      current_label: currentLabel,
      previous_label: 'Kỳ trước',
      current_week_label: currentLabel,
      previous_week_label: 'Kỳ trước',
      series: [],
      days: [],
      summary: {
        total_current: 0,
        total_previous: 0,
        total_current_week: 0,
        total_previous_week: 0,
        growth_percentage: null,
        baseline_status: 'empty',
        peak_day_current: '',
        peak_plays_current: 0,
      },
    };
  }

  if (periodType === 'month') {
    const currBuckets = isCurrent ? [135, 162, 148, 175, 65] : [110, 130, 125, 115, 60];
    const prevBuckets = isCurrent ? [105, 128, 112, 135, 60] : [0, 0, 0, 0, 0];
    const totalPrev = prevBuckets.reduce((a, b) => a + b, 0);
    const series = currBuckets.map((val, idx) => ({
      index: idx + 1,
      label: idx === 4 ? '29 - Cuối tháng' : `Tuần ${idx + 1} (${idx * 7 + 1}-${idx * 7 + 7})`,
      short_label: `Tuần ${idx + 1}`,
      full_label: idx === 4 ? 'Ngày 29 đến cuối tháng' : `Ngày ${idx * 7 + 1} - ${idx * 7 + 7}`,
      current_plays: val,
      previous_plays: prevBuckets[idx],
      diff: val - prevBuckets[idx],
    }));

    return {
      time_range: 'month',
      period_type: 'month',
      granularity: 'week_of_month',
      current_label: currentLabel,
      previous_label: 'Tháng liền trước',
      current_week_label: currentLabel,
      previous_week_label: 'Tháng liền trước',
      series,
      days: [],
      summary: {
        total_current: totalPlays,
        total_previous: totalPrev,
        total_current_week: totalPlays,
        total_previous_week: totalPrev,
        growth_percentage: totalPrev === 0 ? null : 26.9,
        baseline_status: totalPrev === 0 ? 'new_activity' : 'normal',
        peak_label: 'Tuần 4',
        peak_plays: Math.max(...currBuckets),
        peak_day_current: 'Tuần 4',
        peak_plays_current: Math.max(...currBuckets),
      },
    };
  }

  if (periodType === 'year') {
    const currMonths = isCurrent
      ? [180, 195, 210, 225, 240, 260, 235, 250, 265, 290, 255, 235]
      : [140, 155, 165, 175, 185, 195, 180, 190, 195, 210, 185, 175];
    const prevMonths = isCurrent
      ? [135, 145, 160, 170, 180, 195, 175, 190, 200, 220, 190, 190]
      : [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    const totalPrev = prevMonths.reduce((a, b) => a + b, 0);
    const series = currMonths.map((val, idx) => ({
      index: idx + 1,
      label: `Tháng ${idx + 1}`,
      short_label: `T${idx + 1}`,
      full_label: `Tháng ${idx + 1}`,
      current_plays: val,
      previous_plays: prevMonths[idx],
      diff: val - prevMonths[idx],
    }));

    return {
      time_range: 'year',
      period_type: 'year',
      granularity: 'month',
      current_label: currentLabel,
      previous_label: 'Năm trước',
      current_week_label: currentLabel,
      previous_week_label: 'Năm trước',
      series,
      days: [],
      summary: {
        total_current: totalPlays,
        total_previous: totalPrev,
        total_current_week: totalPlays,
        total_previous_week: totalPrev,
        growth_percentage: totalPrev === 0 ? null : 32.1,
        baseline_status: totalPrev === 0 ? 'new_activity' : 'normal',
        peak_label: 'Tháng 10',
        peak_plays: Math.max(...currMonths),
        peak_day_current: 'Tháng 10',
        peak_plays_current: Math.max(...currMonths),
      },
    };
  }

  // Week mode
  const currDays = isCurrent ? [28, 42, 35, 48, 65, 55, 38] : [22, 34, 28, 40, 52, 44, 30];
  const prevDays = isCurrent ? [20, 35, 30, 38, 50, 45, 32] : [18, 25, 22, 30, 38, 32, 25];
  const dayNames = [
    ['Thứ 2', 'Mon'],
    ['Thứ 3', 'Tue'],
    ['Thứ 4', 'Wed'],
    ['Thứ 5', 'Thu'],
    ['Thứ 6', 'Fri'],
    ['Thứ 7', 'Sat'],
    ['Chủ Nhật', 'Sun'],
  ];
  const totalPrev = prevDays.reduce((a, b) => a + b, 0);
  const growth = isCurrent ? 24.4 : 31.6;

  return {
    time_range: '7d',
    period_type: 'week',
    granularity: 'day',
    current_label: currentLabel,
    previous_label: 'Tuần trước',
    current_week_label: currentLabel,
    previous_week_label: 'Tuần trước',
    days: dayNames.map(([vn, en], idx) => ({
      day_index: idx + 1,
      day_name: vn,
      day_name_en: en,
      current_week_plays: currDays[idx],
      previous_week_plays: prevDays[idx],
      diff: currDays[idx] - prevDays[idx],
    })),
    summary: {
      total_current: totalPlays,
      total_previous: totalPrev,
      total_current_week: totalPlays,
      total_previous_week: totalPrev,
      growth_percentage: growth,
      baseline_status: 'normal',
      peak_label: 'Thứ 6',
      peak_plays: currDays[4],
      peak_day_current: 'Thứ 6',
      peak_plays_current: currDays[4],
    },
  };
}

/** Sinh bộ dữ liệu Demo đồng bộ hoàn chỉnh theo từng kỳ Tuần / Tháng / Năm và kỳ rỗng 0 lượt. */
export function getDemoSnapshotForPeriod(
  period: CalendarPeriodItem | null,
  periodType: CalendarPeriodType
): DemoPeriodBundle {
  const totalPlays = period?.play_count ?? (periodType === 'year' ? 2840 : periodType === 'month' ? 685 : 311);
  const isCurrent = period?.is_current ?? true;
  const periodLabel = period?.label || (periodType === 'year' ? 'Năm nay' : periodType === 'month' ? 'Tháng này' : 'Tuần này');
  const periodKey = period?.key || 'demo';

  if (totalPlays <= 0) {
    return {
      summary: {
        total_plays: 0,
        total_duration_ms: 0,
        total_hours: 0,
        unique_artists_count: 0,
        unique_albums_count: 0,
        unique_tracks_count: 0,
        time_range: periodKey,
      },
      topTracks: [],
      topArtists: [],
      topAlbums: [],
      radarData: {
        time_range: periodKey,
        total_tracks_analyzed: 0,
        features: [],
      },
      heatmapData: {
        time_range: periodKey,
        period_type: periodType,
        max_density: 0,
        matrix: [],
      },
      weeklyComparison: buildComparisonForDemo(periodType, periodLabel, 0, isCurrent),
      genreData: { genres: [], total_plays: 0, top_genre: 'Chưa có dữ liệu' },
      musicFacts: [],
      agentMeta: {
        agent_name: 'Aura Music Detective',
        provider_used: 'db-analytics-preview',
        model_name: 'demo',
        iterations_used: 0,
        tools_called: [],
        is_fallback: false,
      },
    };
  }

  const ratio = totalPlays / 311;
  const avgDurationMs = 238000;
  const totalDurationMs = totalPlays * avgDurationMs;
  const totalHours = Number((totalDurationMs / (1000 * 60 * 60)).toFixed(2));
  const uniqueTracks = periodType === 'year' ? 512 : periodType === 'month' ? 184 : isCurrent ? 96 : 78;
  const uniqueArtists = periodType === 'year' ? 145 : periodType === 'month' ? 68 : isCurrent ? 42 : 34;
  const uniqueAlbums = periodType === 'year' ? 132 : periodType === 'month' ? 59 : isCurrent ? 35 : 29;

  const matrix = buildDeterministicWeekMatrix(periodType === 'week' ? totalPlays : 185);
  const maxDensity = Math.max(...matrix.map((c) => c.count), 1);

  return {
    summary: {
      total_plays: totalPlays,
      total_duration_ms: totalDurationMs,
      total_hours: totalHours,
      unique_artists_count: uniqueArtists,
      unique_albums_count: uniqueAlbums,
      unique_tracks_count: uniqueTracks,
      time_range: periodKey,
    },
    topTracks: DEMO_TRACK_BASE.map((t) => ({
      ...t,
      play_count: Math.max(1, Math.round(t.play_count * ratio)),
    })),
    topArtists: DEMO_ARTIST_BASE.map((a) => ({
      ...a,
      play_count: Math.max(1, Math.round(a.play_count * ratio)),
    })),
    topAlbums: DEMO_ALBUM_BASE.map((al) => ({
      ...al,
      play_count: Math.max(1, Math.round(al.play_count * ratio)),
    })),
    radarData: {
      time_range: periodKey,
      total_tracks_analyzed: totalPlays,
      features: [
        { attribute: 'valence', score: isCurrent ? 0.65 : 0.58, description: 'Tích cực, vui tươi' },
        { attribute: 'energy', score: isCurrent ? 0.78 : 0.71, description: 'Sôi động, mạnh mẽ' },
        { attribute: 'danceability', score: isCurrent ? 0.72 : 0.68, description: 'Dễ nhảy, nhịp điệu rõ' },
        { attribute: 'acousticness', score: isCurrent ? 0.35 : 0.44, description: 'Mộc mạc, ít điện tử' },
        { attribute: 'tempo_normalized', score: isCurrent ? 0.62 : 0.59, description: 'Tốc độ nhịp BPM chuẩn hóa' },
      ],
      provenance: {
        spotify: 0,
        dsp_preview: Math.round(totalPlays * 0.95),
        estimated: Math.max(0, totalPlays - Math.round(totalPlays * 0.95)),
        legacy_unknown: 0,
        unavailable: 0,
        total_plays: totalPlays,
        measured_percentage: 95.0,
        has_estimates: true,
        has_legacy_unknown: false,
      },
    },
    heatmapData: {
      time_range: periodKey,
      period_type: periodType,
      max_density: maxDensity,
      matrix,
      month_calendar: periodType === 'month' ? buildDeterministicMonthCalendar(periodKey, totalPlays) : undefined,
      year_calendar: periodType === 'year' ? buildDeterministicYearCalendar(periodKey, totalPlays) : undefined,
    },
    weeklyComparison: buildComparisonForDemo(periodType, periodLabel, totalPlays, isCurrent),
    genreData: scaleGenreDistribution(totalPlays, !isCurrent),
    musicFacts: [
      {
        id: `fact-1-${periodKey}`,
        category: 'repeat_loop',
        badge: 'Vòng Lặp Vô Tận',
        title: `Cơn Nghiện ${DEMO_TRACK_BASE[0].name}`,
        description: `Trong ${periodLabel}, bạn đã nghe lặp lại bản nhạc này nhiều lần nhất mà không bỏ qua.`,
        metric_highlight: `${Math.max(4, Math.round(7 * (isCurrent ? 1 : 0.8)))} lần / ngày`,
        evidence: `${DEMO_TRACK_BASE[0].artists[0]} (${periodLabel})`,
      },
      {
        id: `fact-2-${periodKey}`,
        category: 'artist_dominance',
        badge: 'Độ Trung Thành Tuyệt Đối',
        title: `Gắn Bó Với ${DEMO_ARTIST_BASE[0].name}`,
        description: `${DEMO_ARTIST_BASE[0].name} dẫn đầu danh sách phát trong ${periodLabel} với ${Math.round(62 * ratio)} lượt nghe.`,
        metric_highlight: `${Math.round((62 * ratio * 100) / totalPlays)}% lượt phát`,
        evidence: `${Math.round(62 * ratio)} trên tổng số ${totalPlays} lượt`,
      },
      {
        id: `fact-3-${periodKey}`,
        category: 'marathon',
        badge: 'Kỷ Lục Marathon',
        title: 'Phiên Nghe Liên Tục Cuối Tuần',
        description: `Bạn đắm chìm trong âm nhạc suốt 3.8 giờ liên tiếp với các giai điệu sôi động (${periodLabel}).`,
        metric_highlight: '3.8 giờ liên tục',
        evidence: 'Khung giờ tối 20:00 - 23:45',
      },
    ],
    agentMeta: {
      agent_name: 'Aura Music Detective',
      provider_used: 'groq',
      model_name: 'openai/gpt-oss-120b',
      iterations_used: 2,
      tools_called: ['query_repeat_loops', 'query_artist_dominance'],
      is_fallback: false,
    },
  };
}
