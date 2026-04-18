import { useNavigate } from "react-router-dom";
import { Shield, Terminal } from "lucide-react";

export default function DemoOne() {
  const navigate = useNavigate();

  return (
    <div className="relative w-full h-screen overflow-hidden bg-background flex flex-col items-center justify-center text-white">
      <video 
        autoPlay 
        loop 
        muted 
        playsInline 
        className="absolute inset-0 w-full h-full object-cover z-0 opacity-50 mix-blend-screen"
      >
        <source src="https://res.cloudinary.com/dfonotyfb/video/upload/v1775585556/dds3_1_rqhg7x.mp4" type="video/mp4" />
      </video>
      
      <div className="absolute inset-0 z-10 bg-gradient-to-b from-[#030712]/50 via-transparent to-[#030712]/90" />
      
      <div className="relative z-20 flex flex-col items-center text-center px-6 max-w-5xl mx-auto mt-8 space-y-8 scale-in-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
          <Shield className="w-4 h-4 text-[#38bdf8]" />
          <span className="text-xs font-mono tracking-widest uppercase text-slate-300">Offline Incident Triage Engine</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-sans font-bold tracking-tight text-white drop-shadow-2xl leading-[1.1]">
          Log Sentinel <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-br from-[#38bdf8] to-[#818cf8]">
            Threat Intelligence
          </span>
        </h1>
        
        <p className="text-lg md:text-xl text-slate-300 font-light max-w-2xl leading-relaxed">
          The ultimate cybersecurity platform for proactive threat hunting. Detect credential stuffing, impossible travel, and traffic anomalies with explainable AI scoring and SOC-ready reporting.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center gap-4 pt-8">
          <button 
            onClick={() => navigate("/dashboard")}
            className="group relative inline-flex h-14 items-center justify-center overflow-hidden rounded-lg bg-[#38bdf8] px-8 font-medium text-slate-950 transition-all hover:scale-[1.02] shadow-[0_0_20px_rgba(56,189,248,0.3)] hover:shadow-[0_0_40px_rgba(56,189,248,0.6)]"
          >
            <span className="flex items-center gap-2 text-base font-semibold">
              Enter Operations Center
              <Terminal className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </span>
            <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-150%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(150%)]">
              <div className="relative h-full w-8 bg-white/20" />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
