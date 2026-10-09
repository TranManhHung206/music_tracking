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
import type { AudioFeatureItem } from '../../types/analytics';

export type { AudioFeatureItem };

export interface RadarChartProps {
  data: AudioFeatureItem[];
  title?: string;
}

// Bang anh xa ten thuoc tinh ky thuat sang thuat ngu tieng Viet de hieu
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
}) => {
  // Format du lieu voi ten nhan tieng Viet than thien
  const chartData = data.map((item) => {
    const meta = ATTRIBUTE_MAP[item.attribute] || { label: item.attribute, desc: '' };
    return {
      ...item,
      displayName: meta.label,
      desc: meta.desc,
    };
  });

  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/20 font-semibold">
            Chuẩn Hóa 5D
          </span>
        </div>
        <p className="text-xs sm:text-sm text-slate-400 mb-2">
          Phân tích đa chiều các đặc tính âm thanh theo chuẩn thuật toán Spotify
        </p>
      </div>

      <div className="w-full h-80 my-2">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="82%" data={chartData}>
            <PolarGrid stroke="#334155" strokeDasharray="3 3" />
            <PolarRadiusAxis
              domain={[0, 1]}
              tick={false}
              axisLine={false}
            />
            <PolarAngleAxis
              dataKey="displayName"
              tick={{ fill: '#E2E8F0', fontSize: 13, fontWeight: 600 }}
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
                return [
                  `${(Number(value) * 100).toFixed(0)}%`,
                  item.displayName,
                ];
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-3 border-t border-[#1E293B] text-[11px] text-center">
        {chartData.map((item) => (
          <div
            key={item.attribute}
            className="p-2 rounded-xl bg-[#0B0F17]/60 border border-slate-800/80 hover:border-[#1DB954]/40 transition-colors"
          >
            <span className="block font-semibold text-slate-300 truncate" title={item.desc}>
              {item.displayName}
            </span>
            <span className="text-[#1DB954] font-black text-xs block mt-0.5">
              {(item.score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
