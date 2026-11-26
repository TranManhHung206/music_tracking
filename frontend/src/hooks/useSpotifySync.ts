import { useState, useCallback, useEffect, useRef, type MutableRefObject } from 'react';
import type { UserProfile } from '../types/auth';
import type { CalendarPeriodType, CalendarPeriodItem } from '../types/analytics';
import type { ToastMessage } from '../components/ui/Toast';
import { api } from '../services/api';
import {
  hasSamePeriodQueryScope,
  resolveActivePeriodAfterSync,
} from './dashboardDataState';

interface UseSpotifySyncOptions {
  user: UserProfile | null;
  isDemoMode: boolean;
  periodType: CalendarPeriodType;
  selectedPeriod: CalendarPeriodItem | null;
  hasAutoSyncedRef: MutableRefObject<boolean>;
  setAvailablePeriods: (periods: CalendarPeriodItem[]) => void;
  setSelectedPeriod: (period: CalendarPeriodItem | null) => void;
  refreshAllData: (period: CalendarPeriodItem | null, options?: { clearPeriodData?: boolean }) => Promise<void>;
  addToast: (type: ToastMessage['type'], message: string) => void;
}

/** Quản lý đồng bộ thủ công và đồng bộ ngầm tự động Spotify không chặn giao diện. */
export function useSpotifySync({
  user,
  isDemoMode,
  periodType,
  selectedPeriod,
  hasAutoSyncedRef,
  setAvailablePeriods,
  setSelectedPeriod,
  refreshAllData,
  addToast,
}: UseSpotifySyncOptions) {
  const [isSyncing, setIsSyncing] = useState(false);
  const periodTypeRef = useRef(periodType);
  const selectedPeriodRef = useRef(selectedPeriod);

  useEffect(() => {
    periodTypeRef.current = periodType;
    selectedPeriodRef.current = selectedPeriod;
  }, [periodType, selectedPeriod]);

  const syncPeriodsAndRefresh = useCallback(
    async (awaitRefresh: boolean) => {
      const targetPeriodType = periodTypeRef.current;
      const updatedPeriods = await api.getAvailablePeriods(targetPeriodType, 12);
      if (periodTypeRef.current !== targetPeriodType) return;

      setAvailablePeriods(updatedPeriods);
      const currentPeriod = selectedPeriodRef.current;
      const activePeriod = resolveActivePeriodAfterSync(currentPeriod, updatedPeriods);
      const sameQueryScope = hasSamePeriodQueryScope(currentPeriod, activePeriod);

      if (activePeriod && activePeriod !== currentPeriod) {
        setSelectedPeriod(activePeriod);
      }

      // Chỉ gọi refresh trực tiếp khi kỳ truy vấn giữ nguyên; nếu đổi kỳ, useDashboardData tự tải qua effect
      if (sameQueryScope) {
        const refreshTask = refreshAllData(activePeriod, { clearPeriodData: false });
        if (awaitRefresh) {
          await refreshTask;
        }
      }
    },
    [setAvailablePeriods, setSelectedPeriod, refreshAllData]
  );

  // Đồng bộ ngầm 1 lần duy nhất sau khi xác thực người dùng
  useEffect(() => {
    if (!user || hasAutoSyncedRef.current) return;
    hasAutoSyncedRef.current = true;

    const runAutoSync = async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} lượt nghe mới!`);
          await syncPeriodsAndRefresh(false);
        }
      } catch {
        // Bỏ qua lỗi sync ngầm khởi tạo
      }
    };
    void runAutoSync();
  }, [user, hasAutoSyncedRef, addToast, syncPeriodsAndRefresh]);

  // Đồng bộ định kỳ mỗi 15 phút khi tab đang mở
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} bài hát mới từ Spotify.`);
          await syncPeriodsAndRefresh(false);
        }
      } catch {
        // Bỏ qua lỗi polling ngầm
      }
    }, 900000);

    return () => clearInterval(interval);
  }, [user, addToast, syncPeriodsAndRefresh]);

  const handleSync = useCallback(async () => {
    if (isDemoMode && !user) {
      addToast('warning', 'Chế độ Xem thử không đồng bộ bài hát thật. Vui lòng đăng nhập Spotify để đồng bộ.');
      return;
    }

    setIsSyncing(true);
    try {
      const res = await api.triggerSync();
      const count = res.scrobbled_count ?? 0;
      addToast('success', `Đồng bộ thành công! Đã ghi nhận ${count} bài hát mới từ Spotify.`);
      await syncPeriodsAndRefresh(true);
    } catch (err: unknown) {
      const apiErr = err as { status?: number; message?: string };
      if (apiErr?.status === 429) {
        addToast(
          'warning',
          apiErr.message || 'Spotify đang tạm giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau.'
        );
      } else if (apiErr?.status === 503 || apiErr?.status === 504) {
        addToast(
          'warning',
          apiErr.message || 'Kết nối tới Spotify đang tạm thời gián đoạn. Vui lòng thử lại sau ít phút.'
        );
      } else {
        const msg = err instanceof Error ? err.message : 'Lỗi kết nối';
        addToast('error', `Đồng bộ thất bại: ${msg}`);
      }
    } finally {
      setIsSyncing(false);
    }
  }, [isDemoMode, user, addToast, syncPeriodsAndRefresh]);

  return { isSyncing, handleSync };
}
