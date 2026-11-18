import React from 'react';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from 'recharts';
import { AudioLines } from 'lucide-react';
import type { AudioFeatureItem, FeaturesProvenance } from '../../types/analytics';
import { Card } from '../ui/Card';
import { ChartCardSkeleton } from '../ui/Skeleton';
import { SectionEmptyState, SectionErrorState } from '../ui/SectionState';

export type { AudioFeatureItem };

export interface RadarChartProps {
  data: AudioFeatureItem[];
  title?: string;
  totalTracksAnalyzed?: number;
  provenance?: FeaturesProvenance;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const AXIS_ORDER = ['valence', 'energy', 'danceability', 'acousticness', 'tempo_normalized'] as const;

const ATTRIBUTE_MAP: Record<string, { label: string; desc: string }> = {
  valence: { label: 'Tươi Vui', desc: 'Cảm xúc hân hoan, tích cực' },
  energy: { label: 'Năng Lượng', desc: 'Độ sôi động & bùng nổ' },
  danceability: { label: 'Bắt Tai', desc: 'Độ nảy & bắt nhịp khiêu vũ' },
  acousticness: { label: 'Mộc Mạc', desc: 'Chất nhạc mộc & nhạc cụ acoustic' },
  tempo_normalized: { label: 'Nhịp Điệu', desc: 'Tốc độ nhịp BPM chuẩn hóa (thang 0-200)' },
};

interface ChartRow {
  attribute: string;
  score: number;
  displayName: string;
  desc: string;
}

interface RadarTooltipProps {
  active?: boolean;
  payload?: Array<{
    value?: number;
    payload?: ChartRow;
  }>;
}

const RadarCustomTooltip: React.FC<RadarTooltipProps> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0]?.payload;
  if (!item) return null;
  const pct = (Number(item.score) * 100).toFixed(0);
  const isTempo = item.attribute === 'tempo_normalized';

  return (
    <div className="bg-obsidian-bg/95 border border-obsidian-border rounded-xl p-3 shadow-2xl max-w-[230px]">
      <div className="flex items-center justify-between gap-3 mb-1">
        <span className="text-xs font-bold text-white">{item.displayName}</span>
        <span className="text-xs font-mono font-bold text-spotify-green">
          {pct}%{isTempo ? ` (~${Math.round(Number(item.score) * 200)} BPM)` : ''}
        </span>
      </div>
      {item.desc && <p className="text-[11px] text-text-muted leading-snug">{item.desc}</p>}
    </div>
  );
};

export const RadarChartComponent: React.FC<RadarChartProps> = ({
  data,
  title = 'Âm Hưởng Âm Nhạc (Audio Features)',
  totalTracksAnalyzed,
  provenance,
  isLoading = false,
  error = null,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <Card variant="default" padding="md">
        <ChartCardSkeleton heightClass="h-72" />
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="default" padding="md" className="flex flex-col justify-between">
        <div className="mb-3">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
        </div>
        <SectionErrorState message={error} onRetry={onRetry} />
      </Card>
    );
  }

  const safeData = Array.isArray(data) ? data : [];

  const normalizedMap = new Map<string, AudioFeatureItem>();
  for (const item of safeData) {
    const rawKey = (item.attribute || '').toLowerCase();
    const mappedKey = rawKey === 'tempo' ? 'tempo_normalized' : rawKey;
    normalizedMap.set(mappedKey, { ...item, attribute: mappedKey });
  }

  const orderedItems: AudioFeatureItem[] = [];
  for (const axisKey of AXIS_ORDER) {
    const match = normalizedMap.get(axisKey);
    if (match) {
      orderedItems.push(match);
      normalizedMap.delete(axisKey);
    }
  }
  normalizedMap.forEach((extra) => orderedItems.push(extra));

  const chartData: ChartRow[] = orderedItems.map((item) => {
    const meta = ATTRIBUTE_MAP[item.attribute] || {
      label: item.attribute,
      desc: item.description || '',
    };
    const clampedScore = Math.min(Math.max(Number(item.score) || 0, 0), 1);
    return {
      attribute: item.attribute,
      score: clampedScore,
      displayName: meta.label,
      desc: meta.desc,
    };
  });

  const isEmpty = totalTracksAnalyzed === 0 || chartData.length === 0;
  const hasEstimates = Boolean(provenance?.has_estimates || provenance?.has_legacy_unknown);

  const sortedByScore = [...chartData].sort((a, b) => b.score - a.score);
  const highestDim = sortedByScore[0];
  const lowestDim = sortedByScore[sortedByScore.length - 1];

  return (
    <Card variant="default" padding="md" className="flex flex-col justify-between">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-spotify-green/10 text-spotify-green border border-spotify-green/25 font-semibold shrink-0">
            {provenance && provenance.total_plays > 0
              ? `Đo trực tiếp ${provenance.measured_percentage}%`
              : 'Chuẩn Hóa 5D'}
          </span>
        </div>
        <p className="text-xs sm:text-sm text-text-muted mb-2 leading-relaxed">
          {hasEstimates && provenance
            ? `Phân tích 5 chiều từ ${provenance.spotify + provenance.dsp_preview} lượt đo trực tiếp và ${provenance.estimated + provenance.legacy_unknown} lượt ước lượng/bổ sung.`
            : 'Phân tích đa chiều 5 đặc tính âm thanh chuẩn hóa [0 - 100%] từ bản nhạc đã phát.'}
        </p>
      </div>

      {isEmpty ? (
        <SectionEmptyState
          title="Chưa đủ dữ liệu để phân tích âm hưởng"
          description="Không có lượt nghe nào được ghi nhận trong khoảng thời gian đang chọn."
          icon={<AudioLines className="w-5 h-5" />}
        />
      ) : (
        <>
          <div className="w-full h-64 sm:h-72 my-1">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="74%" data={chartData}>
                <PolarGrid stroke="#334155" strokeDasharray="3 3" />
                <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
                <PolarAngleAxis
                  dataKey="displayName"
                  tick={{ fill: '#E2E8F0', fontSize: 12, fontWeight: 600 }}
                />
                <Radar
                  name="Chỉ số"
                  dataKey="score"
                  stroke="#1DB954"
                  strokeWidth={2.5}
                  fill="#1DB954"
                  fillOpacity={0.35}
                  dot={{ r: 3.5, fill: '#1DB954', strokeWidth: 0 }}
                />
                <Tooltip content={<RadarCustomTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {highestDim && lowestDim && (
            <p className="text-xs text-slate-300 bg-obsidian-bg/50 border border-obsidian-border/70 rounded-xl px-3 py-2 mb-3">
              Nổi bật nhất:{' '}
              <strong className="text-spotify-green">
                {highestDim.displayName} ({(highestDim.score * 100).toFixed(0)}%)
              </strong>
              {highestDim.attribute !== lowestDim.attribute && (
                <>
                  {' '}
                  • Thấp nhất:{' '}
                  <strong className="text-white">
                    {lowestDim.displayName} ({(lowestDim.score * 100).toFixed(0)}%)
                  </strong>
                </>
              )}
            </p>
          )}

          <div className="grid grid-cols-2 min-[420px]:grid-cols-3 sm:grid-cols-5 gap-2 pt-3 border-t border-obsidian-border text-xs text-center">
            {chartData.map((item) => (
              <div
                key={item.attribute}
                className="p-2 rounded-xl bg-obsidian-bg/60 border border-slate-800/80 hover:border-spotify-green/40 transition-colors"
                title={item.desc}
              >
                <span className="block font-semibold text-slate-200 truncate text-[11px]">
                  {item.displayName}
                </span>
                <span className="text-spotify-green font-black text-xs block mt-0.5 font-mono">
                  {(item.score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};
