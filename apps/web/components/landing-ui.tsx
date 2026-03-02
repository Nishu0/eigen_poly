"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

export function LandingUI() {
  return (
    <div className="ui-layer absolute inset-0 z-10 font-mono text-[#1a1a1a] flex flex-col pointer-events-none">
      
      {/* Header */}
      <header className="flex justify-between items-center p-6 md:p-10 uppercase text-xs md:text-sm tracking-wider font-semibold">
        <div className="flex items-center gap-3 bg-[#E6E2D6]/80 px-4 py-2 rounded-full border border-[#1a1a1a]/10 backdrop-blur-sm pointer-events-auto">
          <div className="w-2.5 h-2.5 rounded-full bg-[#CC5A38] animate-pulse"></div>
          <span>EIGENPOLY // PREDICTION PROTOCOL</span>
        </div>
        
        <div className="flex gap-6 md:gap-10 pointer-events-auto">
          <Link href="/dashboard" className="hover:text-[#CC5A38] transition-colors border-b border-transparent hover:border-[#CC5A38]">MARKETS</Link>
          <Link href="/dashboard" className="hover:text-[#CC5A38] transition-colors border-b border-transparent hover:border-[#CC5A38]">AGENTS</Link>
          <Link href="/dashboard" className="hover:text-[#CC5A38] transition-colors border-b border-transparent hover:border-[#CC5A38]">DEVELOPERS</Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative flex items-center justify-center p-6 lg:p-12 overflow-hidden">
        
        {/* Left Data Block */}
        <div className="absolute left-6 md:left-12 lg:left-24 top-1/2 -translate-y-1/2 text-[10px] md:text-xs leading-relaxed uppercase max-w-[200px] pointer-events-auto">
          <p className="mb-4">
            NETWORK: POLYGON<br />
            CURRENCY: USDC.E<br />
            STATUS: LIVE
          </p>
          <p className="font-bold text-[#CC5A38]">[AI PREDICTIONS]</p>
        </div>

        {/* Hero Title */}
        <div className="relative flex flex-col items-center justify-center pointer-events-auto text-center z-10 pointer-events-none">
          <h1 className="text-[12vw] md:text-[15vw] leading-none font-black text-[#1a1a1a] tracking-tighter" style={{ fontFamily: "var(--font-display, serif)", textShadow: "4px 4px 0px rgba(255,255,255,0.4)" }}>
            EIGEN<br className="md:hidden"/>POLY
          </h1>
          
          <div className="pt-8 flex flex-wrap justify-center gap-2 md:gap-4 pointer-events-auto max-w-[90vw]">
            <span className="px-4 md:px-6 py-2 border-2 border-[#1a1a1a] rounded-full text-xs md:text-sm font-bold uppercase bg-[#E6E2D6] whitespace-nowrap">
              Beta Mainnet
            </span>
            <span className="px-4 md:px-6 py-2 border-2 border-[#CC5A38] text-[#CC5A38] rounded-full text-xs md:text-sm font-bold uppercase bg-[#E6E2D6] whitespace-nowrap">
              Agent Trading
            </span>
            <span className="px-4 md:px-6 py-2 border-2 border-[#1a1a1a] rounded-full text-xs md:text-sm font-bold uppercase bg-[#E6E2D6] whitespace-nowrap flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>
              Status: Active
            </span>
          </div>

          <div className="mt-12 pointer-events-auto">
             <Link href="/dashboard" className="group relative inline-flex items-center justify-center px-8 py-4 font-bold text-white bg-[#1a1a1a] rounded-full overflow-hidden transition-all hover:scale-105">
                <span className="relative z-10 flex items-center gap-2">
                  START TRADING <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </span>
                <div className="absolute inset-0 bg-[#CC5A38] translate-y-[100%] group-hover:translate-y-0 transition-transform duration-300 ease-in-out z-0"></div>
             </Link>
          </div>
        </div>

        {/* Right Data Block */}
        <div className="absolute right-6 md:right-12 lg:right-24 top-1/2 -translate-y-1/2 text-right text-[10px] md:text-xs leading-relaxed uppercase max-w-[200px] pointer-events-auto">
          <p className="mb-4">
            LIQUIDITY: 10M+<br />
            UPTIME: 99.9%<br />
            AGENTS ACTIVE: 2.4K
          </p>
          <Link href="/dashboard" className="font-bold border-b border-[#1a1a1a] pb-0.5 hover:text-[#CC5A38] hover:border-[#CC5A38] transition-colors inline-block pointer-events-auto">[LAUNCH APP]</Link>
        </div>
      </main>

      {/* Footer / Map Section */}
      <div className="relative h-[20vh] w-full mt-auto overflow-hidden">
        {/* Mountains / Map graphic */}
        <div className="absolute bottom-0 left-0 w-full h-full pointer-events-none">
          <svg preserveAspectRatio="none" width="100%" height="100%" viewBox="0 0 1440 320" xmlns="http://www.w3.org/2000/svg">
            <path fill="#2A5A43" d="M0,288L120,277.3C240,267,480,245,720,240C960,235,1200,245,1320,250.7L1440,256L1440,320L1320,320C1200,320,960,320,720,320C480,320,240,320,120,320L0,320Z"></path>
            <path fill="#CC5A38" d="M0,192L80,192C160,192,320,192,480,213.3C640,235,800,277,960,282.7C1120,288,1280,256,1360,240L1440,224L1440,320L1360,320C1280,320,1120,320,960,320C800,320,640,320,480,320C320,320,160,320,80,320L0,320Z"></path>
          </svg>
        </div>
        
        <div className="absolute inset-0 flex justify-between items-end p-6 md:p-10 uppercase text-[10px] md:text-xs text-[#E6E2D6] font-semibold mix-blend-difference">
          <div>
            EIGEN LAYER<br />
            POLYGON<br />
            MAINNET
          </div>
          <div className="flex-1 flex justify-center pb-2">
            <div className="w-12 h-12 rounded-full border-2 border-[#E6E2D6]/50 flex items-center justify-center relative pointer-events-auto hover:border-[#E6E2D6] transition-colors cursor-crosshair">
              <div className="w-full h-0.5 bg-[#E6E2D6]/50 absolute rotate-45"></div>
            </div>
          </div>
          <div className="text-right">
            PREDICT THE FUTURE<br />
            DECENTRALIZED<br />
            ALWAYS ON
          </div>
        </div>
      </div>
    </div>
  );
}
