import React, { useRef, useState } from 'react';
import html2canvas from 'html2canvas-pro';
import { Download, Sparkles, Music, X, Disc, Mic2, Music2, Headphones, Clock, Flame } from 'lucide-react';

export type AspectRatioType = '9:16' | '4:5' | '1:1' | '16:9';

export interface FavoriteItemData {
  name: string;
  artist?: string;
  playCount?: number;
}

export interface ShareableCardProps {
  userName: string;
  avatarUrl?: string;
  personaTitle: string;
  tagline: string;
  topArtists: string[];
  topGenres?: string[];
  period: string;
  isOpen: boolean;
  onClose: () => void;
  totalPlays?: number;
  totalHours?: number;
  topGenre?: string;
  topTrack?: FavoriteItemData;
  topArtist?: FavoriteItemData;
  topAlbum?: FavoriteItemData;
}

// Chuyen tieng Viet co dau thanh khong dau de ten file khong bi loi tren moi he dieu hanh
const sanitizeFileName = (name: string): string => {
  return name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_');
};

export const ShareableCard: React.FC<ShareableCardProps> = ({
  userName,
  avatarUrl,
  personaTitle,
  tagline,
  topArtists,
  topGenres,
  period,
  isOpen,
  onClose,
  totalPlays = 0,
  totalHours = 0,
  topGenre,
  topTrack,
  topArtist,
  topAlbum,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [aspectRatio, setAspectRatio] = useState<AspectRatioType>('9:16');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [exportedDataUrl, setExportedDataUrl] = useState<string | null>(null);

  if (!isOpen) return null;

  // Fallback du lieu yeu thich neu khong truyen props cu the
  const resolvedTopArtistName = topArtist?.name || topArtists[0] || 'Nghệ sĩ yêu thích';
  const resolvedTopArtistPlays = topArtist?.playCount;

  const resolvedTopGenre = topGenre || (topGenres && topGenres[0]) || 'Pop / EDM';

  const handleDownloadImage = async () => {
    if (!cardRef.current) return;
    setIsExporting(true);
    setDownloadSuccess(false);
    setDownloadError(null);
    try {
      const canvas = await html2canvas(cardRef.current, {
        scale: 2,
        useCORS: true,
        allowTaint: false,
        backgroundColor: '#0B0F17',
        logging: false,
      });

      const cleanRatio = aspectRatio.replace(':', '_');
      const safeName = sanitizeFileName(userName) || 'user';
      const fileName = `music_persona_${safeName}_${cleanRatio}.png`;

      // Tao Data URL tu canvas
      const dataUrl = canvas.toDataURL('image/png');
      setExportedDataUrl(dataUrl);

      const link = document.createElement('a');
      link.style.display = 'none';
      link.download = fileName;
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();

      setTimeout(() => {
        if (document.body.contains(link)) {
          document.body.removeChild(link);
        }
      }, 1000);

      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 8000);
    } catch (err: unknown) {
      console.error('Lỗi khi xuất ảnh thẻ chia sẻ:', err);
      const errMsg = err instanceof Error ? err.message : 'Không xác định';
      setDownloadError(errMsg);
    } finally {
      setIsExporting(false);
    }
  };

  const handleOpenInNewTab = () => {
    if (!exportedDataUrl) return;
    const newWindow = window.open();
    if (newWindow) {
      newWindow.document.write(
        `<title>Music Persona Card Preview</title><body style="margin:0;background:#0B0F17;display:flex;align-items:center;justify-content:center;min-height:100vh;"><img src="${exportedDataUrl}" style="max-width:95vw;max-height:95vh;border-radius:16px;box-shadow:0 10px 40px rgba(0,0,0,0.8);" /><p style="position:fixed;bottom:16px;color:#94a3b8;font-family:sans-serif;font-size:13px;">Nhấn Ctrl + S hoặc chuột phải vào ảnh để chọn nơi lưu theo ý muốn</p></body>`
      );
    }
  };

  // Kich thuoc gon gang khong bi tran man hinh laptop
  const getContainerStyle = () => {
    switch (aspectRatio) {
      case '1:1':
        return 'w-[320px] h-[320px] sm:w-[360px] sm:h-[360px]';
      case '4:5':
        return 'w-[310px] h-[388px] sm:w-[335px] sm:h-[418px]';
      case '16:9':
        return 'w-[440px] h-[248px] sm:w-[490px] sm:h-[276px]';
      case '9:16':
      default:
        return 'w-[300px] h-[533px] sm:w-[320px] sm:h-[568px]';
    }
  };

  const getDownloadLabel = () => {
    switch (aspectRatio) {
      case '1:1':
        return 'Lưu ảnh Vuông Post (1:1)';
      case '4:5':
        return 'Lưu ảnh Dọc Chân dung (4:5 / 3:4)';
      case '16:9':
        return 'Lưu ảnh Ngang Banner (16:9)';
      case '9:16':
      default:
        return 'Lưu ảnh Story (9:16)';
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="min-h-full flex flex-col items-center justify-center p-3 sm:p-4 py-6 pb-24">
        <div className="flex flex-col items-center max-w-lg w-full">
          {/* Top Controls: Ratio Selector & Close */}
          <div className="w-full flex items-center justify-between mb-4 px-2">
            {/* Aspect Ratio Tabs */}
            <div className="flex items-center space-x-1.5 p-1 rounded-xl bg-[#131B2E] border border-slate-800">
              {(['9:16', '4:5', '1:1', '16:9'] as AspectRatioType[]).map((ratio) => (
                <button
                  key={ratio}
                  onClick={() => setAspectRatio(ratio)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    aspectRatio === ratio
                      ? 'bg-[#1DB954] text-black shadow-md shadow-[#1DB954]/20'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  {ratio === '4:5' ? '4:5 (3:4)' : ratio}
                </button>
              ))}
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-full bg-[#131B2E] text-slate-400 hover:text-white transition-all cursor-pointer ml-3"
              title="Đóng"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Khung Card Dynamic Aspect Ratio */}
          <div
            ref={cardRef}
            id="shareable-card-canvas"
            className={`${getContainerStyle()} bg-gradient-to-b from-[#0F172A] via-[#131B2E] to-[#0B0F17] border-2 border-emerald-500/30 rounded-3xl p-4 sm:p-5 flex flex-col justify-between shadow-2xl relative overflow-hidden text-white transition-all duration-300`}
          >
            {/* Background Neon Glow */}
            <div className="absolute -top-16 -right-16 w-44 h-44 bg-[#1DB954]/25 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-16 -left-16 w-44 h-44 bg-purple-600/25 rounded-full blur-3xl pointer-events-none" />

            {/* Header */}
            <div className="flex items-center justify-between z-10 border-b border-slate-800/80 pb-2.5">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 rounded-lg bg-[#1DB954]/20 border border-[#1DB954]/40 flex items-center justify-center text-[#1DB954]">
                  <Music className="w-3.5 h-3.5" />
                </div>
                <div>
                  <p className="text-[8px] sm:text-[9px] text-slate-400 font-mono tracking-widest uppercase leading-none">
                    MUSIC TRACKER
                  </p>
                  <h4 className="text-[11px] sm:text-xs font-bold text-white leading-none mt-0.5">
                    AI WRAPPED
                  </h4>
                </div>
              </div>
              <span className="text-[9px] sm:text-[10px] px-2 py-0.5 bg-white/10 rounded-full text-slate-300 font-medium">
                {period}
              </span>
            </div>

            {/* 1. Layout Landscape (16:9) */}
            {aspectRatio === '16:9' ? (
              <div className="grid grid-cols-2 gap-3.5 my-auto z-10 items-center">
                {/* Cot trai: Thong tin nguoi dung & AI Persona */}
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={userName}
                        className="w-8 h-8 rounded-full border-2 border-[#1DB954] object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-[#1DB954]/20 border-2 border-[#1DB954] flex items-center justify-center text-xs font-bold text-[#1DB954]">
                        {userName.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <span className="text-[9px] text-slate-400 block leading-tight">Thính giả</span>
                      <h3 className="text-xs font-bold text-white leading-tight truncate">{userName}</h3>
                    </div>
                  </div>

                  <div className="bg-[#0B0F17]/60 border border-slate-800/80 rounded-xl p-2.5">
                    <div className="inline-flex items-center space-x-1 text-[8px] uppercase tracking-widest text-purple-400 font-bold mb-0.5">
                      <Sparkles className="w-2.5 h-2.5" />
                      <span>AI Music Persona</span>
                    </div>
                    <h2 className="text-xs sm:text-sm font-black text-white leading-tight truncate">
                      {personaTitle}
                    </h2>
                    <p className="text-[10px] text-emerald-300/90 italic truncate mt-0.5">
                      "{tagline}"
                    </p>
                  </div>
                </div>

                {/* Cot phai: 3 chi so & Bo ba yeu thich */}
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-1 bg-slate-900/60 p-1.5 rounded-lg border border-slate-800 text-center">
                    <div>
                      <span className="text-[8px] text-slate-400 block">Lượt nghe</span>
                      <span className="text-[10px] font-bold text-white">{totalPlays}</span>
                    </div>
                    <div>
                      <span className="text-[8px] text-slate-400 block">Thời lượng</span>
                      <span className="text-[10px] font-bold text-white">{totalHours}h</span>
                    </div>
                    <div>
                      <span className="text-[8px] text-slate-400 block">Gu nhạc</span>
                      <span className="text-[10px] font-bold text-emerald-400 truncate block">{resolvedTopGenre}</span>
                    </div>
                  </div>

                  <div className="bg-slate-900/60 rounded-xl p-2 border border-slate-800 space-y-1">
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Music2 className="w-3 h-3 text-[#1DB954] shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{topTrack?.name || 'Bài hát nổi bật'}</span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Mic2 className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{resolvedTopArtistName}</span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Disc className="w-3 h-3 text-purple-400 shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{topAlbum?.name || 'Album tiêu biểu'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : aspectRatio === '1:1' ? (
              /* 2. Layout Vuong (1:1) */
              <div className="grid grid-cols-2 gap-3 my-auto z-10 items-stretch">
                {/* Cot trai */}
                <div className="flex flex-col justify-between space-y-2">
                  <div className="flex items-center space-x-2">
                    {avatarUrl ? (
                      <img
                        src={avatarUrl}
                        alt={userName}
                        className="w-8 h-8 rounded-full border-2 border-[#1DB954] object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-[#1DB954]/20 border-2 border-[#1DB954] flex items-center justify-center text-xs font-bold text-[#1DB954]">
                        {userName.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <span className="text-[9px] text-slate-400 block leading-tight">Thính giả</span>
                      <h3 className="text-xs font-bold text-white leading-tight truncate">{userName}</h3>
                    </div>
                  </div>

                  <div className="bg-[#0B0F17]/60 border border-slate-800/80 rounded-xl p-2.5">
                    <div className="inline-flex items-center space-x-1 text-[8px] uppercase tracking-widest text-purple-400 font-bold mb-0.5">
                      <Sparkles className="w-2.5 h-2.5" />
                      <span>AI Persona</span>
                    </div>
                    <h2 className="text-xs sm:text-sm font-black text-white leading-tight">
                      {personaTitle}
                    </h2>
                    <p className="text-[10px] text-emerald-300/90 italic leading-snug mt-1 line-clamp-2">
                      "{tagline}"
                    </p>
                  </div>
                </div>

                {/* Cot phai: Thong so & Bo ba yeu thich */}
                <div className="flex flex-col justify-between space-y-2">
                  <div className="grid grid-cols-3 gap-1 bg-slate-900/60 p-1.5 rounded-lg border border-slate-800 text-center">
                    <div>
                      <span className="text-[8px] text-slate-400 block">Lượt</span>
                      <span className="text-[10px] font-bold text-white">{totalPlays}</span>
                    </div>
                    <div>
                      <span className="text-[8px] text-slate-400 block">Giờ</span>
                      <span className="text-[10px] font-bold text-white">{totalHours}h</span>
                    </div>
                    <div>
                      <span className="text-[8px] text-slate-400 block">Dòng nhạc</span>
                      <span className="text-[10px] font-bold text-emerald-400 truncate block">{resolvedTopGenre}</span>
                    </div>
                  </div>

                  <div className="bg-slate-900/70 rounded-xl p-2.5 border border-slate-800 space-y-1.5">
                    <span className="text-[8px] uppercase tracking-wider text-slate-400 font-bold block mb-1">
                      Bộ Ba Yêu Thích
                    </span>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Music2 className="w-3 h-3 text-[#1DB954] shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{topTrack?.name || 'Bài hát nổi bật'}</span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Mic2 className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{resolvedTopArtistName}</span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-[10px]">
                      <Disc className="w-3 h-3 text-purple-400 shrink-0" />
                      <span className="font-semibold text-slate-200 truncate">{topAlbum?.name || 'Album tiêu biểu'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* 3. Layout Dọc: Story (9:16) & Chân dung (4:5) */
              <div className="flex flex-col justify-between flex-1 my-1.5 z-10 space-y-2.5">
                {/* Hang 1: Profile & 3 Chi So Nhanh */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt={userName}
                          className="w-9 h-9 rounded-full border-2 border-[#1DB954] object-cover"
                        />
                      ) : (
                        <div className="w-9 h-9 rounded-full bg-[#1DB954]/20 border-2 border-[#1DB954] flex items-center justify-center text-xs font-bold text-[#1DB954]">
                          {userName.charAt(0).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <span className="text-[9px] text-slate-400 block leading-tight">Thính giả</span>
                        <h3 className="text-xs sm:text-sm font-bold text-white leading-tight">{userName}</h3>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[9px] text-slate-400 block leading-tight">Dòng nhạc</span>
                      <span className="text-[11px] font-bold text-[#1DB954]">{resolvedTopGenre}</span>
                    </div>
                  </div>

                  {/* 3 O Thong So Micro-Stats */}
                  <div className="grid grid-cols-3 gap-1.5 bg-[#0B0F17]/60 p-2 rounded-xl border border-slate-800/80 text-center">
                    <div className="flex flex-col items-center">
                      <div className="flex items-center space-x-1 text-slate-400 text-[9px]">
                        <Headphones className="w-2.5 h-2.5" />
                        <span>Lượt nghe</span>
                      </div>
                      <span className="text-xs font-black text-white mt-0.5">{totalPlays.toLocaleString()}</span>
                    </div>
                    <div className="flex flex-col items-center border-x border-slate-800/80">
                      <div className="flex items-center space-x-1 text-slate-400 text-[9px]">
                        <Clock className="w-2.5 h-2.5" />
                        <span>Thời lượng</span>
                      </div>
                      <span className="text-xs font-black text-white mt-0.5">{totalHours} giờ</span>
                    </div>
                    <div className="flex flex-col items-center">
                      <div className="flex items-center space-x-1 text-slate-400 text-[9px]">
                        <Flame className="w-2.5 h-2.5 text-amber-400" />
                        <span>Tần suất</span>
                      </div>
                      <span className="text-xs font-black text-amber-300 mt-0.5">Sôi nổi</span>
                    </div>
                  </div>
                </div>

                {/* Hang 2: Khối Độc Bản AI Music Persona (Giữ nguyên vẹn) */}
                <div className="text-center py-2.5 bg-[#0B0F17]/70 border border-purple-500/30 rounded-2xl p-3 shadow-lg relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-purple-600/10 rounded-full blur-xl pointer-events-none" />
                  <div className="inline-flex items-center space-x-1 text-[9px] uppercase tracking-widest text-purple-400 font-bold mb-1">
                    <Sparkles className="w-3 h-3" />
                    <span>AI Music Persona</span>
                  </div>
                  <h2 className="text-sm sm:text-base font-black text-white tracking-tight leading-tight mb-1">
                    {personaTitle}
                  </h2>
                  <p className="text-[11px] sm:text-xs text-emerald-300/90 italic font-medium leading-relaxed">
                    "{tagline}"
                  </p>
                </div>

                {/* Hang 3: Bộ Ba Yêu Thích Trong Kỳ (Bài hát, Nghệ sĩ, Album) */}
                <div className="bg-slate-900/70 rounded-2xl p-3 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">
                      Bộ Ba Yêu Thích Trong Kỳ
                    </span>
                    <span className="text-[9px] text-[#1DB954] font-semibold">Top Picks</span>
                  </div>

                  <div className="space-y-1.5">
                    {/* 1. Bai hat yeu thich */}
                    <div className="flex items-center justify-between bg-[#0B0F17]/50 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="flex items-center space-x-2 min-w-0">
                        <div className="w-5 h-5 rounded-md bg-[#1DB954]/20 flex items-center justify-center text-[#1DB954] shrink-0">
                          <Music2 className="w-3 h-3" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-[11px] font-bold text-white truncate leading-tight">
                            {topTrack?.name || 'Bài hát nổi bật'}
                          </p>
                          <p className="text-[9px] text-slate-400 truncate leading-tight">
                            {topTrack?.artist || 'Nghệ sĩ'}
                          </p>
                        </div>
                      </div>
                      {topTrack?.playCount !== undefined && (
                        <span className="text-[9px] font-semibold text-slate-300 ml-2 shrink-0">
                          {topTrack.playCount} lượt
                        </span>
                      )}
                    </div>

                    {/* 2. Nghe si yeu thich */}
                    <div className="flex items-center justify-between bg-[#0B0F17]/50 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="flex items-center space-x-2 min-w-0">
                        <div className="w-5 h-5 rounded-md bg-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
                          <Mic2 className="w-3 h-3" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-[11px] font-bold text-white truncate leading-tight">
                            {resolvedTopArtistName}
                          </p>
                          <p className="text-[9px] text-slate-400 leading-tight">Nghệ sĩ đồng hành #1</p>
                        </div>
                      </div>
                      {resolvedTopArtistPlays !== undefined && (
                        <span className="text-[9px] font-semibold text-slate-300 ml-2 shrink-0">
                          {resolvedTopArtistPlays} lượt
                        </span>
                      )}
                    </div>

                    {/* 3. Album yeu thich */}
                    <div className="flex items-center justify-between bg-[#0B0F17]/50 p-1.5 rounded-lg border border-slate-800/60">
                      <div className="flex items-center space-x-2 min-w-0">
                        <div className="w-5 h-5 rounded-md bg-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
                          <Disc className="w-3 h-3" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-[11px] font-bold text-white truncate leading-tight">
                            {topAlbum?.name || 'Album tiêu biểu'}
                          </p>
                          <p className="text-[9px] text-slate-400 truncate leading-tight">
                            {topAlbum?.artist || 'Nhiều nghệ sĩ'}
                          </p>
                        </div>
                      </div>
                      {topAlbum?.playCount !== undefined && (
                        <span className="text-[9px] font-semibold text-slate-300 ml-2 shrink-0">
                          {topAlbum.playCount} lượt
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Visualizer Accent Bar (Thay the dong text AI cu) */}
            <div className="z-10 pt-2 flex items-center justify-center space-x-1 opacity-60">
              <span className="w-1 h-2 bg-[#1DB954] rounded-full" />
              <span className="w-1 h-3.5 bg-[#1DB954] rounded-full" />
              <span className="w-1 h-5 bg-[#1DB954] rounded-full" />
              <span className="w-1 h-2.5 bg-purple-400 rounded-full" />
              <span className="w-1 h-4 bg-purple-400 rounded-full" />
              <span className="w-1 h-2 bg-[#1DB954] rounded-full" />
            </div>
          </div>

          {/* Action Download Buttons */}
          <div className="w-full flex flex-col space-y-2.5 mt-4">
            <button
              onClick={handleDownloadImage}
              disabled={isExporting}
              className={`w-full py-3.5 px-6 rounded-2xl font-bold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-xl disabled:opacity-50 ${
                downloadSuccess
                  ? 'bg-emerald-500 text-black shadow-emerald-500/25'
                  : 'bg-[#1DB954] hover:bg-[#1ED760] text-black shadow-[#1DB954]/25'
              }`}
            >
              <Download className="w-4 h-4" />
              <span>
                {isExporting
                  ? 'Đang tạo ảnh...'
                  : downloadSuccess
                  ? 'Đã tải ảnh về thư mục Downloads!'
                  : getDownloadLabel()}
              </span>
            </button>

            {exportedDataUrl && (
              <button
                onClick={handleOpenInNewTab}
                className="w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-slate-800/80 hover:bg-slate-700 text-slate-200 transition-all cursor-pointer border border-slate-700/60 flex items-center justify-center space-x-1.5"
              >
                <span>Mở ảnh xem toàn màn hình (Ctrl + S để lưu tùy chọn)</span>
              </button>
            )}

            {downloadError && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-800 text-xs text-red-200 text-center">
                Có lỗi khi xuất ảnh: {downloadError}
              </div>
            )}

            <p className="text-[11px] text-slate-400 text-center px-4 leading-relaxed">
              Ảnh sẽ được tải thẳng về thư mục Downloads của máy tính. Bạn có thể nhấn Ctrl + J để xem file ngay sau khi bấm lưu.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
