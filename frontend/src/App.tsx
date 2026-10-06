import { Music, Activity, Cpu, ShieldCheck } from 'lucide-react'

export function App() {
  return (
    <div className="min-h-screen bg-[#0B0F17] text-[#F8FAFC] p-8 flex flex-col items-center justify-center">
      <div className="max-w-3xl w-full bg-[#131B2E] border border-[#1E293B] rounded-2xl p-8 shadow-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-[#1E293B] pb-6">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/30 flex items-center justify-center text-[#1DB954]">
              <Music className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Music Analytics Dashboard</h1>
              <p className="text-sm text-[#94A3B8]">Spotify Tracker & AI Insights Platform</p>
            </div>
          </div>
          <span className="px-3 py-1 text-xs font-semibold rounded-full bg-[#1DB954]/10 text-[#1DB954] border border-[#1DB954]/20">
            Phase 0: Sẵn sàng
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[#0B0F17]/60 border border-[#1E293B] rounded-xl p-4 space-y-2">
            <div className="flex items-center space-x-2 text-[#1DB954]">
              <Activity className="w-5 h-5" />
              <span className="font-semibold text-sm">Hạ tầng Backend</span>
            </div>
            <p className="text-xs text-[#94A3B8]">Django 5, Celery, Redis và SQLite/PostgreSQL đã được kết nối.</p>
          </div>

          <div className="bg-[#0B0F17]/60 border border-[#1E293B] rounded-xl p-4 space-y-2">
            <div className="flex items-center space-x-2 text-[#1DB954]">
              <Cpu className="w-5 h-5" />
              <span className="font-semibold text-sm">AI Engine</span>
            </div>
            <p className="text-xs text-[#94A3B8]">Sẵn sàng với Groq openai/gpt-oss-120b và Gemini Fallback.</p>
          </div>

          <div className="bg-[#0B0F17]/60 border border-[#1E293B] rounded-xl p-4 space-y-2">
            <div className="flex items-center space-x-2 text-[#1DB954]">
              <ShieldCheck className="w-5 h-5" />
              <span className="font-semibold text-sm">Bảo mật Token</span>
            </div>
            <p className="text-xs text-[#94A3B8]">Mã hóa Fernet AES-256 đã kích hoạt cho Access/Refresh Token.</p>
          </div>
        </div>

        <div className="pt-4 flex justify-between items-center text-xs text-[#94A3B8] border-t border-[#1E293B]">
          <span>Giao diện Obsidian Dark Mode (#0B0F17)</span>
          <span>Tailwind CSS v4 + Vite + React 19</span>
        </div>
      </div>
    </div>
  )
}

export default App
