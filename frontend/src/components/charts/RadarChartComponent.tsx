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

const ATTRIBUTE_MAP: Record<string, { label: string; desc: string }> = {
  energy: { label: 'Năng Lượng', desc: 'Độ sôi động & bùng nổ' },
  danceability: { label: 'Bắt Tai', desc: 'Độ nảy & bắt nhịp khiêu vũ' },
  valence: { label: 'Tươi Vui', desc: 'Cảm xúc hân hoan, tích cực' },
  acousticness: { label: 'Mộc Mạc', desc: 'Chất nhạc mộc & nhạc cụ acoustic' },
  tempo_normalized: { label: 'Nhịp Điệu', desc: 'Tốc độ nhịp & BPM' },
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

  const chartData = safeData.map((item) => {
    const key = (item.attribute || '').toLowerCase();
    const mappedKey = key === 'tempo' ? 'tempo_normalized' : key;
    const meta = ATTRIBUTE_MAP[mappedKey] || { label: item.attribute, desc: item.description || '' };
    return {
      ...item,
      displayName: meta.label,
      desc: meta.desc,
    };
  });

  const isEmpty = totalTracksAnalyzed === 0 || chartData.length === 0;
  const hasEstimates = Boolean(provenance?.has_estimates || provenance?.has_legacy_unknown);

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
          {hasEstimates
            ? 'Phân tích 5 chiều âm thanh từ Audio DSP và ước lượng bổ sung cho các bài thiếu bản nghe thử.'
            : 'Phân tích đa chiều các đặc tính âm thanh từ tín hiệu Audio DSP và siêu dữ liệu bản nhạc.'}
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
          <div className="w-full h-72 sm:h-80 my-2">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="78%" data={chartData}>
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
                  strokeWidth={2}
                  fill="#1DB954"
                  fillOpacity={0.4}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0B0F17',
                    borderColor: '#1E293B',
                    borderRadius: '12px',
                    color: '#F8FAFC',
                    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                  }}
                  formatter={(value, _name, entry) => {
                    const item = entry.payload as { displayName: string; desc: string };
                    return [`${(Number(value) * 100).toFixed(0)}%`, item.displayName];
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

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
