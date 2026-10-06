import React from 'react';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Tooltip,
} from 'recharts';
import type { AudioFeatureItem } from '../../types/analytics';

export type { AudioFeatureItem };

export interface RadarChartProps {
  data: AudioFeatureItem[];
  title?: string;
}

export const RadarChartComponent: React.FC<RadarChartProps> = ({
  data,
  title = 'Âm Hưởng Âm Nhạc (Audio Features)',
}) => {
  return (
    <div className="w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h3>
        <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/20 font-semibold">
          Chuẩn Hóa 5D
        </span>
      </div>
      <p className="text-xs sm:text-sm text-slate-400 mb-4">
        Phân tích đa chiều các đặc tính âm thanh theo chuẩn thuật toán Spotify
      </p>

      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid stroke="#334155" />
            <PolarAngleAxis
              dataKey="attribute"
              tick={{ fill: '#94A3B8', fontSize: 12, fontWeight: 500 }}
            />
            <Radar
              name="Chỉ số"
              dataKey="score"
              stroke="#1DB954"
              fill="#1DB954"
              fillOpacity={0.45}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0B0F17',
                borderColor: '#1E293B',
                borderRadius: '8px',
                color: '#F8FAFC',
              }}
              formatter={(value) => [`${(Number(value) * 100).toFixed(0)}%`, 'Điểm số']}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-2 pt-4 border-t border-[#1E293B] text-[11px] text-slate-400 text-center">
        {data.map((item) => (
          <div key={item.attribute} className="p-1 rounded bg-[#0B0F17]/50">
            <span className="block font-semibold text-slate-300">{item.attribute}</span>
            <span className="text-[#1DB954] font-bold">{(item.score * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};
