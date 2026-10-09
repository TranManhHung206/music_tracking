import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown, Check } from 'lucide-react';
import type { CalendarPeriodType, CalendarPeriodItem } from '../../types/analytics';

interface CalendarPeriodSelectorProps {
  periodType: CalendarPeriodType;
  onPeriodTypeChange: (type: CalendarPeriodType) => void;
  selectedPeriod: CalendarPeriodItem | null;
  onPeriodSelect: (period: CalendarPeriodItem) => void;
  periods: CalendarPeriodItem[];
  isLoading?: boolean;
}

function formatDateRange(startStr: string, endStr: string): string {
  try {
    const [sy, sm, sd] = startStr.split('-');
    const [ey, em, ed] = endStr.split('-');
    if (sy === ey) {
      return `${sd}/${sm} - ${ed}/${em}/${ey}`;
    }
    return `${sd}/${sm}/${sy} - ${ed}/${em}/${ey}`;
  } catch {
    return `${startStr} - ${endStr}`;
  }
}

export const CalendarPeriodSelector: React.FC<CalendarPeriodSelectorProps> = ({
  periodType,
  onPeriodTypeChange,
  selectedPeriod,
  onPeriodSelect,
  periods,
  isLoading = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const tabs: { id: CalendarPeriodType; label: string }[] = [
    { id: 'week', label: 'Tuần' },
    { id: 'month', label: 'Tháng' },
    { id: 'year', label: 'Năm' },
  ];

  // Dong dropdown khi nhan ra ngoai
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5 justify-start sm:justify-end">
      <span className="text-xs sm:text-sm font-semibold text-slate-300 shrink-0 hidden md:inline">
        Khung thời gian:
      </span>

      {/* Tabs Chon Tuan / Thang / Nam */}
      <div className="h-9 inline-flex items-center p-1 rounded-xl bg-[#0B0F17] border border-[#1E293B] shrink-0">
        {tabs.map((tab) => {
          const isActive = periodType === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                if (periodType !== tab.id) {
                  onPeriodTypeChange(tab.id);
                  setIsOpen(false);
                }
              }}
              className={`h-7 px-3.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center justify-center ${
                isActive
                  ? 'bg-[#1DB954] text-black shadow-md shadow-[#1DB954]/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Dropdown Menu Chon Cu The Khoang Thoi Gian */}
      <div className="relative shrink-0" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen((prev) => !prev)}
          disabled={isLoading || periods.length === 0}
          className="h-9 inline-flex items-center space-x-2 px-3.5 rounded-xl bg-[#0B0F17] border border-[#1E293B] hover:border-slate-700 text-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer disabled:opacity-50"
        >
          <Calendar className="w-3.5 h-3.5 text-[#1DB954] shrink-0" />
          <span className="truncate max-w-[130px] sm:max-w-[180px]">
            {selectedPeriod ? selectedPeriod.label : 'Chọn kỳ thống kê'}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown Popup Danh Sach Tu Hien Tai Ve Qua Khu - Luon can le phai (right-0) */}
        {isOpen && (
          <div className="absolute right-0 mt-2 w-76 sm:w-80 max-h-80 overflow-y-auto rounded-xl bg-[#131B2E] border border-[#1E293B] shadow-2xl p-1.5 z-50 divide-y divide-slate-800/40">
            {periods.length === 0 ? (
              <div className="p-3 text-xs text-slate-400 text-center">
                Không tìm thấy kỳ thống kê khả dụng
              </div>
            ) : (
              periods.map((item) => {
                const isSelected = selectedPeriod?.key === item.key;
                return (
                  <button
                    key={item.key}
                    onClick={() => {
                      onPeriodSelect(item);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2.5 rounded-lg text-left text-xs transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#1DB954]/15 text-[#1DB954] font-bold'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`}
                  >
                    <div className="flex flex-col space-y-0.5 min-w-0 flex-1 pr-3">
                      <div className="flex items-center space-x-1.5 min-w-0">
                        <span className="truncate font-semibold">{item.label}</span>
                        {item.is_current && (
                          <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-[#1DB954]/20 text-[#1DB954] font-bold border border-[#1DB954]/30 leading-none">
                            Hiện tại
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {formatDateRange(item.start_date, item.end_date)}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0 ml-auto">
                      <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                        item.play_count > 0 ? 'bg-slate-800 text-slate-200' : 'bg-slate-900/60 text-slate-400'
                      }`}>
                        {item.play_count} lượt
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[#1DB954] shrink-0" />}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
};
