import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown, Check } from 'lucide-react';
import type { CalendarPeriodType, CalendarPeriodItem } from '../../types/analytics';
import { SegmentedControl, type SegmentedOption } from './SegmentedControl';

interface CalendarPeriodSelectorProps {
  periodType: CalendarPeriodType;
  onPeriodTypeChange: (type: CalendarPeriodType) => void;
  selectedPeriod: CalendarPeriodItem | null;
  onPeriodSelect: (period: CalendarPeriodItem) => void;
  periods: CalendarPeriodItem[];
  isLoading?: boolean;
}

const PERIOD_TABS: SegmentedOption<CalendarPeriodType>[] = [
  { id: 'week', label: 'Tuần' },
  { id: 'month', label: 'Tháng' },
  { id: 'year', label: 'Năm' },
];

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

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, []);

  return (
    <div className="w-full sm:w-auto flex flex-wrap sm:flex-nowrap items-center gap-2.5 justify-between sm:justify-end">
      <span className="text-xs sm:text-sm font-semibold text-slate-300 shrink-0 hidden md:inline">
        Khung thời gian:
      </span>

      <SegmentedControl<CalendarPeriodType>
        options={PERIOD_TABS}
        value={periodType}
        onChange={(nextType) => {
          onPeriodTypeChange(nextType);
          setIsOpen(false);
        }}
        ariaLabel="Chọn chế độ Tuần, Tháng hoặc Năm"
        className="h-9 shrink-0"
      />

      {/* Dropdown chọn kỳ cụ thể, căn trái trên mobile để không tràn mép trái */}
      <div className="relative min-w-0 shrink-0" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          disabled={isLoading || periods.length === 0}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-label="Chọn kỳ thống kê cụ thể"
          className="h-9 inline-flex items-center gap-2 px-3 sm:px-3.5 rounded-xl bg-obsidian-bg border border-obsidian-border hover:border-slate-700 text-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green"
        >
          <Calendar className="w-3.5 h-3.5 text-spotify-green shrink-0" />
          <span className="truncate max-w-[130px] sm:max-w-[180px]">
            {selectedPeriod ? selectedPeriod.label : 'Chọn kỳ thống kê'}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {isOpen && (
          <div
            role="listbox"
            aria-label="Danh sách kỳ thống kê"
            className="absolute left-0 sm:left-auto sm:right-0 mt-2 w-[min(20rem,calc(100vw-1.5rem))] max-h-80 overflow-y-auto scrollbar-thin rounded-xl bg-obsidian-card border border-obsidian-border shadow-2xl p-1.5 z-50 divide-y divide-slate-800/40 animate-slide-up"
          >
            {periods.length === 0 ? (
              <div className="p-3 text-xs text-text-muted text-center">
                Không tìm thấy kỳ thống kê khả dụng
              </div>
            ) : (
              periods.map((item) => {
                const isSelected = selectedPeriod?.key === item.key;
                return (
                  <button
                    key={item.key}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onPeriodSelect(item);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2.5 rounded-lg text-left text-xs transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-spotify-green ${
                      isSelected
                        ? 'bg-spotify-green/15 text-spotify-green font-bold'
                        : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                    }`}
                  >
                    <div className="flex flex-col gap-0.5 min-w-0 flex-1 pr-3">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="truncate font-semibold">{item.label}</span>
                        {item.is_current && (
                          <span className="shrink-0 px-1.5 py-0.5 rounded text-[11px] bg-spotify-green/20 text-spotify-green font-bold border border-spotify-green/30 leading-none">
                            Hiện tại
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-text-muted">
                        {formatDateRange(item.start_date, item.end_date)}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 ml-auto">
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                          item.play_count > 0
                            ? 'bg-slate-800 text-slate-200'
                            : 'bg-slate-900/60 text-slate-400'
                        }`}
                      >
                        {item.play_count} lượt
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-spotify-green shrink-0" />}
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
