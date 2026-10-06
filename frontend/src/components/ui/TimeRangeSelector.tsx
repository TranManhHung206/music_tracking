import React from 'react';
import type { TimeRange } from '../../types/analytics';

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({ value, onChange }) => {
  const options: { id: TimeRange; label: string }[] = [
    { id: '7d', label: '7 Ngày' },
    { id: '30d', label: '30 Ngày' },
    { id: '1y', label: '1 Năm' },
  ];

  return (
    <div className="inline-flex p-1 rounded-xl bg-[#0B0F17] border border-[#1E293B]">
      {options.map((opt) => {
        const isActive = value === opt.id;
        return (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              isActive
                ? 'bg-[#1DB954] text-black shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};
