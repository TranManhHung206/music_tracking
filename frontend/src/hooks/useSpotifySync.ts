import { useState, useCallback, useEffect, type MutableRefObject } from 'react';
import type { UserProfile } from '../types/auth';
import type { CalendarPeriodType, CalendarPeriodItem } from '../types/analytics';
import type { ToastMessage } from '../components/ui/Toast';
import { api } from '../services/api';

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

  // Đồng bộ ngầm 1 lần duy nhất sau khi xác thực người dùng
  useEffect(() => {
    if (!user || hasAutoSyncedRef.current) return;
    hasAutoSyncedRef.current = true;

    const runAutoSync = async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} lượt nghe mới!`);
          const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
          setAvailablePeriods(updatedPeriods);
          const activePeriod =
            (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) ||
            updatedPeriods[0] ||
            null;
          setSelectedPeriod(activePeriod);
          refreshAllData(activePeriod, { clearPeriodData: false });
        }
      } catch {
        // Bỏ qua lỗi sync ngầm khởi tạo
      }
    };
    runAutoSync();
  }, [
    user,
    hasAutoSyncedRef,
    addToast,
    refreshAllData,
    selectedPeriod,
    periodType,
    setAvailablePeriods,
    setSelectedPeriod,
  ]);

  // Đồng bộ định kỳ mỗi 15 phút khi tab đang mở
  useEffect(() => {
    if (!user) return;
    const interval = setInterval(async () => {
      try {
        const syncRes = await api.triggerSync();
        if (syncRes.scrobbled_count > 0) {
          addToast('info', `Auto-Scrobble: Đã đồng bộ thêm ${syncRes.scrobbled_count} bài hát mới từ Spotify.`);
          const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
          setAvailablePeriods(updatedPeriods);
          const activePeriod =
            (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) ||
            updatedPeriods[0] ||
            null;
          setSelectedPeriod(activePeriod);
          refreshAllData(activePeriod, { clearPeriodData: false });
        }
      } catch {
        // Bỏ qua lỗi polling ngầm
      }
    }, 900000);

    return () => clearInterval(interval);
  }, [
    user,
    selectedPeriod,
    periodType,
    refreshAllData,
    addToast,
    setAvailablePeriods,
    setSelectedPeriod,
  ]);

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
      const updatedPeriods = await api.getAvailablePeriods(periodType, 12);
      setAvailablePeriods(updatedPeriods);
      const activePeriod =
        (selectedPeriod && updatedPeriods.find((p) => p.key === selectedPeriod.key)) ||
        updatedPeriods[0] ||
        null;
      setSelectedPeriod(activePeriod);
      await refreshAllData(activePeriod, { clearPeriodData: false });
    } catch (err: unknown) {
      const apiErr = err as { status?: number; message?: string };
      if (apiErr?.status === 429) {
        addToast(
          'warning',
          apiErr.message || 'Spotify đang tạm giới hạn tần suất yêu cầu (Rate Limit). Vui lòng thử lại sau.'
        );
      } else {
        const msg = err instanceof Error ? err.message : 'Lỗi kết nối';
        addToast('error', `Đồng bộ thất bại: ${msg}`);
      }
    } finally {
      setIsSyncing(false);
    }
  }, [
    isDemoMode,
    user,
    addToast,
    periodType,
    selectedPeriod,
    setAvailablePeriods,
    setSelectedPeriod,
    refreshAllData,
  ]);

  return { isSyncing, handleSync };
}
