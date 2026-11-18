import { useState, useCallback, useEffect, useRef } from 'react';
import type { CalendarPeriodType, CalendarPeriodItem } from '../types/analytics';
import type { UserProfile } from '../types/auth';
import { api, isRequestCanceled, getDynamicMockCalendarPeriods } from '../services/api';

interface UseDashboardPeriodOptions {
  user: UserProfile | null;
  isDemoMode: boolean;
  onPeriodsError?: (message: string) => void;
}

/** Quản lý bộ lọc Tuần / Tháng / Năm và danh sách các kỳ thống kê khả dụng. */
export function useDashboardPeriod({
  user,
  isDemoMode,
  onPeriodsError,
}: UseDashboardPeriodOptions) {
  const [periodType, setPeriodType] = useState<CalendarPeriodType>(() => {
    const saved = localStorage.getItem('user_calendar_period_type');
    return saved === 'week' || saved === 'month' || saved === 'year'
      ? (saved as CalendarPeriodType)
      : 'week';
  });

  const [availablePeriods, setAvailablePeriods] = useState<CalendarPeriodItem[]>(() => {
    const dynamicMocks = getDynamicMockCalendarPeriods();
    const saved = localStorage.getItem('user_calendar_period_type') as CalendarPeriodType;
    const type = saved === 'week' || saved === 'month' || saved === 'year' ? saved : 'week';
    return dynamicMocks[type] || [];
  });

  const [selectedPeriod, setSelectedPeriod] = useState<CalendarPeriodItem | null>(() => {
    const dynamicMocks = getDynamicMockCalendarPeriods();
    const saved = localStorage.getItem('user_calendar_period_type') as CalendarPeriodType;
    const type = saved === 'week' || saved === 'month' || saved === 'year' ? saved : 'week';
    const savedMode = localStorage.getItem('user_calendar_selected_mode');
    const savedKey = localStorage.getItem('user_calendar_selected_key');
    const periodsForType = dynamicMocks[type] || [];

    if (savedMode === 'specific' && savedKey) {
      const match = periodsForType.find((p) => p.key === savedKey);
      if (match) return match;
    }
    return periodsForType.find((p) => p.is_current) || periodsForType[0] || null;
  });

  const [isLoadingPeriods, setIsLoadingPeriods] = useState(false);
  const periodRequestIdRef = useRef(0);

  const handlePeriodTypeChange = useCallback((newType: CalendarPeriodType) => {
    setPeriodType(newType);
    localStorage.setItem('user_calendar_period_type', newType);
    localStorage.setItem('user_calendar_selected_mode', 'current');
    localStorage.removeItem('user_calendar_selected_key');

    const dynamicMocks = getDynamicMockCalendarPeriods();
    const fallbackList = dynamicMocks[newType] || [];
    setAvailablePeriods(fallbackList);
    const defaultPeriod = fallbackList.find((p) => p.is_current) || fallbackList[0] || null;
    if (defaultPeriod) {
      setSelectedPeriod(defaultPeriod);
    }
  }, []);

  const handlePeriodSelect = useCallback((period: CalendarPeriodItem) => {
    setSelectedPeriod(period);
    if (period.is_current) {
      localStorage.setItem('user_calendar_selected_mode', 'current');
      localStorage.removeItem('user_calendar_selected_key');
    } else {
      localStorage.setItem('user_calendar_selected_mode', 'specific');
      localStorage.setItem('user_calendar_selected_key', period.key);
    }
  }, []);

  useEffect(() => {
    if (!user) return;

    const controller = new AbortController();
    const reqId = ++periodRequestIdRef.current;

    const fetchPeriods = async () => {
      setIsLoadingPeriods(true);
      try {
        const periods = await api.getAvailablePeriods(periodType, 12, controller.signal);
        if (controller.signal.aborted || reqId !== periodRequestIdRef.current) return;
        if (periods.length > 0) {
          setAvailablePeriods(periods);
          setSelectedPeriod((prev) => {
            const savedMode = localStorage.getItem('user_calendar_selected_mode');
            const savedKey = localStorage.getItem('user_calendar_selected_key');

            if (savedMode === 'specific' && savedKey) {
              const matchedSaved = periods.find((p) => p.key === savedKey);
              if (matchedSaved) return matchedSaved;
            }

            if (prev && !prev.is_current && savedMode === 'specific') {
              const matchedPrev = periods.find((p) => p.key === prev.key);
              if (matchedPrev) return matchedPrev;
            }

            return periods.find((p) => p.is_current) || periods[0];
          });
        }
      } catch (err) {
        if (isRequestCanceled(err) || controller.signal.aborted || reqId !== periodRequestIdRef.current) {
          return;
        }
        const msg = err instanceof Error ? err.message : 'Không thể tải danh sách kỳ thống kê.';
        onPeriodsError?.(msg);
      } finally {
        if (!controller.signal.aborted && reqId === periodRequestIdRef.current) {
          setIsLoadingPeriods(false);
        }
      }
    };

    const timer = setTimeout(() => {
      void fetchPeriods();
    }, 0);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [user, isDemoMode, periodType, onPeriodsError]);

  return {
    periodType,
    setPeriodType,
    availablePeriods,
    setAvailablePeriods,
    selectedPeriod,
    setSelectedPeriod,
    isLoadingPeriods,
    handlePeriodTypeChange,
    handlePeriodSelect,
  };
}
