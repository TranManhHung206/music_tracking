import type { CalendarPeriodType } from '../types/analytics';

/** Định dạng thời lượng nghe thân thiện và nhất quán giữa phút (< 1 giờ) và giờ. */
export function formatListeningDuration(totalDurationMs?: number, totalHours?: number): string {
  if (typeof totalDurationMs === 'number' && totalDurationMs > 0) {
    const minutes = Math.round(totalDurationMs / 60000);
    if (minutes > 0 && minutes < 60) {
      return `${minutes} phút`;
    }
  }
  const safeHours = typeof totalHours === 'number' && Number.isFinite(totalHours) ? totalHours : 0;
  return `${safeHours} giờ`;
}

/** Tính nhãn tần suất nghe động trên thẻ chia sẻ theo tổng lượt phát và chu kỳ. */
export function getListeningFrequencyLabel(
  totalPlays: number,
  periodType: CalendarPeriodType = 'week'
): string {
  if (!totalPlays || totalPlays <= 0) {
    return 'Chưa ghi nhận';
  }
  if (periodType === 'year') {
    if (totalPlays >= 2000) return 'Bất tận';
    if (totalPlays >= 600) return 'Sôi nổi';
    if (totalPlays >= 120) return 'Đều đặn';
    return 'Nhẹ nhàng';
  }
  if (periodType === 'month') {
    if (totalPlays >= 400) return 'Bất tận';
    if (totalPlays >= 150) return 'Sôi nổi';
    if (totalPlays >= 40) return 'Đều đặn';
    return 'Nhẹ nhàng';
  }
  if (totalPlays >= 180) return 'Cuồng nhiệt';
  if (totalPlays >= 60) return 'Sôi nổi';
  if (totalPlays >= 15) return 'Đều đặn';
  return 'Nhẹ nhàng';
}

/** Kiểm tra Spotify ID thật trước khi tạo liên kết mở Spotify. */
export function isRealSpotifyId(id?: string | null): id is string {
  if (!id || typeof id !== 'string') return false;
  if (id.startsWith('mock') || id.startsWith('art_') || id.startsWith('alb_') || id.startsWith('demo_')) {
    return false;
  }
  return /^[A-Za-z0-9]{15,}$/.test(id);
}
