import React, { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import { Download, Sparkles, Music, X } from 'lucide-react';

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
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  const handleDownloadImage = async () => {
    if (!cardRef.current) return;
    setIsExporting(true);
    try {
      const canvas = await html2canvas(cardRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#0B0F17',
      });
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = `music_persona_${userName.toLowerCase().replace(/\s+/g, '_')}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Lỗi khi xuất ảnh thẻ chia sẻ:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="flex flex-col items-center max-w-sm w-full">
        {/* Close Button */}
        <div className="w-full flex justify-end mb-2">
          <button
            onClick={onClose}
            className="p-2 rounded-full bg-[#131B2E] text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Khung Card 9:16 chup anh */}
        <div
          ref={cardRef}
          id="shareable-card-canvas"
          className="w-[340px] h-[600px] bg-gradient-to-b from-[#0F172A] via-[#131B2E] to-[#0B0F17] border-2 border-emerald-500/30 rounded-3xl p-6 flex flex-col justify-between shadow-2xl relative overflow-hidden text-white"
        >
          {/* Background Neon Glow */}
          <div className="absolute -top-16 -right-16 w-44 h-44 bg-[#1DB954]/25 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-16 -left-16 w-44 h-44 bg-purple-600/25 rounded-full blur-3xl pointer-events-none" />

          {/* Header */}
          <div className="flex items-center justify-between z-10 border-b border-slate-800/80 pb-4">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-[#1DB954]/20 border border-[#1DB954]/40 flex items-center justify-center text-[#1DB954]">
                <Music className="w-4 h-4" />
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-mono tracking-widest uppercase">
                  MUSIC TRACKER
                </p>
                <h4 className="text-xs font-bold text-white">AI WRAPPED</h4>
              </div>
            </div>
            <span className="text-[10px] px-2.5 py-0.5 bg-white/10 rounded-full text-slate-300 font-medium">
              {period}
            </span>
          </div>

          {/* User Profile */}
          <div className="flex items-center space-x-3 z-10 my-2">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={userName}
                className="w-11 h-11 rounded-full border-2 border-[#1DB954] object-cover"
              />
            ) : (
              <div className="w-11 h-11 rounded-full bg-[#1DB954]/20 border-2 border-[#1DB954] flex items-center justify-center text-sm font-bold text-[#1DB954]">
                {userName.charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <span className="text-[11px] text-slate-400 block">Thính giả</span>
              <h3 className="text-sm font-bold text-white leading-tight">{userName}</h3>
            </div>
          </div>

          {/* AI Persona Section */}
          <div className="my-auto text-center z-10 py-4 bg-[#0B0F17]/50 border border-slate-800/60 rounded-2xl p-4">
            <div className="inline-flex items-center space-x-1 text-[10px] uppercase tracking-widest text-purple-400 font-bold mb-1">
              <Sparkles className="w-3 h-3" />
              <span>AI Music Persona</span>
            </div>
            <h2 className="text-lg font-black text-white tracking-tight leading-tight mb-2">
              {personaTitle}
            </h2>
            <p className="text-xs text-emerald-300/90 italic font-medium">
              "{tagline}"
            </p>
          </div>

          {/* Top Artists */}
          <div className="z-10 bg-slate-900/60 rounded-2xl p-4 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
              Top Nghệ Sĩ Đồng Hành
            </span>
            <div className="space-y-1.5">
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

          {/* Footer Branding */}
          <div className="text-center z-10 pt-3 border-t border-slate-800/80">
            <p className="text-[10px] text-slate-500 font-mono">
              Spotify Tracker & Groq GPT-OSS-120B AI Insights
            </p>
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleDownloadImage}
          disabled={isExporting}
          className="mt-4 w-full py-3 px-6 rounded-2xl bg-[#1DB954] hover:bg-[#1ED760] text-black font-bold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-xl shadow-[#1DB954]/25 disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          <span>{isExporting ? 'Đang tạo ảnh...' : 'Lưu ảnh Story (9:16)'}</span>
        </button>
      </div>
    </div>
  );
};
