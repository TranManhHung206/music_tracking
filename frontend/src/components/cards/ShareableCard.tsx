import React, { useRef, useState } from 'react';
import html2canvas from 'html2canvas-pro';
import { Download, Sparkles, Music, X, ExternalLink } from 'lucide-react';

export type AspectRatioType = '9:16' | '4:5' | '1:1' | '16:9';

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
  period,
  isOpen,
  onClose,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [aspectRatio, setAspectRatio] = useState<AspectRatioType>('9:16');
  const [isExporting, setIsExporting] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [exportedDataUrl, setExportedDataUrl] = useState<string | null>(null);

  if (!isOpen) return null;

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

  // Kich thuoc gon gang giup khong bi tran man hinh laptop
  const getContainerStyle = () => {
    switch (aspectRatio) {
      case '1:1':
        return 'w-[310px] h-[310px] sm:w-[350px] sm:h-[350px]';
      case '4:5':
        return 'w-[300px] h-[375px] sm:w-[330px] sm:h-[412px]';
      case '16:9':
        return 'w-[440px] h-[248px] sm:w-[490px] sm:h-[276px]';
      case '9:16':
      default:
        return 'w-[290px] h-[480px] sm:w-[310px] sm:h-[515px]';
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
          className={`${getContainerStyle()} bg-gradient-to-b from-[#0F172A] via-[#131B2E] to-[#0B0F17] border-2 border-emerald-500/30 rounded-3xl p-5 flex flex-col justify-between shadow-2xl relative overflow-hidden text-white transition-all duration-300`}
        >
          {/* Background Neon Glow */}
          <div className="absolute -top-16 -right-16 w-44 h-44 bg-[#1DB954]/25 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-16 -left-16 w-44 h-44 bg-purple-600/25 rounded-full blur-3xl pointer-events-none" />

          {/* Header */}
          <div className="flex items-center justify-between z-10 border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#1DB954]/20 border border-[#1DB954]/40 flex items-center justify-center text-[#1DB954]">
                <Music className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[9px] text-slate-400 font-mono tracking-widest uppercase">
                  MUSIC TRACKER
                </p>
                <h4 className="text-xs font-bold text-white">AI WRAPPED</h4>
              </div>
            </div>
            <span className="text-[10px] px-2.5 py-0.5 bg-white/10 rounded-full text-slate-300 font-medium">
              {period}
            </span>
          </div>

          {/* Body Layout for Landscape (16:9) vs Portrait (9:16, 4:5, 1:1) */}
          {aspectRatio === '16:9' ? (
            <div className="grid grid-cols-2 gap-4 my-auto z-10 items-center">
              {/* Left Column: User & Persona */}
              <div className="space-y-2">
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
                    <span className="text-[10px] text-slate-400 block">Thính giả</span>
                    <h3 className="text-xs font-bold text-white leading-tight">{userName}</h3>
                  </div>
                </div>

                <div className="bg-[#0B0F17]/50 border border-slate-800/60 rounded-xl p-3">
                  <div className="inline-flex items-center space-x-1 text-[9px] uppercase tracking-widest text-purple-400 font-bold mb-1">
                    <Sparkles className="w-3 h-3" />
                    <span>AI Persona</span>
                  </div>
                  <h2 className="text-sm font-black text-white leading-tight truncate">
                    {personaTitle}
                  </h2>
                  <p className="text-[11px] text-emerald-300/90 italic truncate">
                    "{tagline}"
                  </p>
                </div>
              </div>

              {/* Right Column: Top Artists */}
              <div className="bg-slate-900/60 rounded-xl p-3 border border-slate-800">
                <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider block mb-1.5">
                  Top Nghệ Sĩ Đồng Hành
                </span>
                <div className="space-y-1">
                  {topArtists.slice(0, 3).map((artist, idx) => (
                    <div key={artist} className="flex items-center space-x-2 text-xs">
                      <span className="text-[10px] font-bold text-[#1DB954]">#{idx + 1}</span>
                      <span className="font-semibold text-slate-200 truncate">{artist}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* User Profile */}
              <div className="flex items-center space-x-3 z-10 my-1">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={userName}
                    className="w-10 h-10 rounded-full border-2 border-[#1DB954] object-cover"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-[#1DB954]/20 border-2 border-[#1DB954] flex items-center justify-center text-xs font-bold text-[#1DB954]">
                    {userName.charAt(0).toUpperCase()}
                  </div>
                )}
                <div>
                  <span className="text-[10px] text-slate-400 block">Thính giả</span>
                  <h3 className="text-sm font-bold text-white leading-tight">{userName}</h3>
                </div>
              </div>

              {/* AI Persona Section */}
              <div className="my-auto text-center z-10 py-3 bg-[#0B0F17]/50 border border-slate-800/60 rounded-2xl p-4">
                <div className="inline-flex items-center space-x-1 text-[10px] uppercase tracking-widest text-purple-400 font-bold mb-1">
                  <Sparkles className="w-3 h-3" />
                  <span>AI Music Persona</span>
                </div>
                <h2 className="text-base sm:text-lg font-black text-white tracking-tight leading-tight mb-1.5">
                  {personaTitle}
                </h2>
                <p className="text-xs text-emerald-300/90 italic font-medium">
                  "{tagline}"
                </p>
              </div>

              {/* Top Artists */}
              <div className="z-10 bg-slate-900/60 rounded-2xl p-3.5 border border-slate-800">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                  Top Nghệ Sĩ Đồng Hành
                </span>
                <div className="space-y-1">
                  {topArtists.slice(0, 3).map((artist, idx) => (
                    <div key={artist} className="flex items-center justify-between text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] font-bold text-[#1DB954]">#{idx + 1}</span>
                        <span className="font-semibold text-slate-200">{artist}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Footer Branding */}
          <div className="text-center z-10 pt-2 border-t border-slate-800/80">
            <p className="text-[9px] text-slate-500 font-mono">
              Spotify Tracker & Groq GPT-OSS-120B AI Insights
            </p>
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
              className="w-full py-2.5 px-4 rounded-xl font-medium text-xs flex items-center justify-center space-x-2 bg-[#131B2E] hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition-all cursor-pointer"
            >
              <ExternalLink className="w-3.5 h-3.5 text-[#1DB954]" />
              <span>Mở ảnh xem toàn màn hình (Bấm Ctrl + S để chọn nơi lưu)</span>
            </button>
          )}
        </div>

        {/* Location Guidance */}
        <div className="w-full mt-3 p-3 rounded-xl bg-[#131B2E] border border-slate-800 text-center">
          <p className="text-xs text-slate-300 leading-relaxed font-medium">
            {downloadError ? (
              <span className="text-rose-400">
                Lỗi khi tạo ảnh: {downloadError}. Vui lòng thử lại hoặc chụp ảnh thẻ.
              </span>
            ) : downloadSuccess ? (
              <span className="text-emerald-400">
                Ảnh đã được tải về máy thành công! Nhấn tổ hợp phím <strong className="text-white underline">Ctrl + J</strong> trên trình duyệt để mở file trong thư mục Downloads.
              </span>
            ) : (
              <span>
                Ảnh sẽ được tải thẳng về thư mục <strong className="text-white">Downloads</strong> của máy tính. Bạn có thể nhấn <strong className="text-white">Ctrl + J</strong> để xem file ngay sau khi bấm lưu.
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  </div>
  );
};
