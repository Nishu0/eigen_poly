"use client";

import { Shield, Globe, Zap } from "lucide-react";

interface LoginPageProps {
  loginUrl: string;
}

const features = [
  {
    title: "On-chain Trading",
    desc: "Split positions, CLOB orders, and automatic approvals on Polygon",
  },
  {
    title: "Market Analysis",
    desc: "Real-time Polymarket data with driven insights + sozu + metengine.",
  },
  {
    title: "TEE Wallet",
    desc: "Hardware-secured key management inside Trusted Execution Environments powered by eigencloud",
  },
];

export function LoginPage({ loginUrl }: LoginPageProps) {
  return (
    <div
      className="flex min-h-screen w-full items-center justify-center"
      style={{ background: "#f5f4f2", padding: "40px" }}
    >
      <div
        className="flex w-full h-full overflow-hidden"
        style={{
          minHeight: "calc(100vh - 80px)",
          borderRadius: "16px",
          border: "1.5px solid #CC5A38",
          boxShadow: "0 8px 40px rgba(0,0,0,0.10)",
        }}
      >
        {/* ── Left Panel ── */}
        <div
          className="relative hidden md:flex w-[48%] flex-col justify-between overflow-hidden"
          style={{
            padding: "48px",
            backgroundColor: "#E7E2D6",
            background: [
              "radial-gradient(circle at 50% 120%, #CC5A38bb 0%, transparent 60%)",
              "radial-gradient(circle at 20% 40%, #2A5A4366 0%, transparent 50%)",
              "radial-gradient(circle at 80% 20%, #E7E2D6 0%, transparent 50%)",
            ].join(", "),
          }}
        >
          <div>
            <h1
              className="text-4xl font-bold leading-tight"
              style={{ color: "#CC5A38", fontFamily: "Georgia, serif" }}
            >
              EigenPoly
            </h1>
          </div>

          <div className="space-y-6">
            {features.map((f, i) => (
              <div key={i}>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: "#CC5A38", fontFamily: "monospace" }}
                >
                  <span className="font-bold">{f.title}:</span> {f.desc}
                </p>
              </div>
            ))}
          </div>

          <div>
            <div
              className="inline-flex items-center px-5 py-2 text-xs font-medium"
              style={{
                border: "1.5px solid #CC5A38",
                borderRadius: "99px",
                color: "#CC5A38",
                fontFamily: "monospace",
              }}
            >
              Beta Access
            </div>
          </div>
        </div>

        {/* ── Right Panel ── */}
        <div
          className="relative flex flex-1 flex-col items-center justify-center"
          style={{ background: "#0f0f0f", padding: "48px" }}
        >
          <div className="mb-8 md:hidden text-center">
            <h1 className="text-3xl font-black text-white tracking-tight font-mono">EIGENPOLY</h1>
          </div>

          <div className="w-full" style={{ maxWidth: 400 }}>
            <div className="mb-10">
              <h2 className="text-4xl font-bold text-white" style={{ fontFamily: "monospace" }}>
                Welcome back
              </h2>
              <p className="mt-3 text-base text-neutral-400" style={{ fontFamily: "monospace" }}>
                Sign in to manage your agents and trade markets.
              </p>
            </div>

            <a
              href={loginUrl}
              className="flex w-full items-center justify-center gap-3 rounded-xl text-base font-bold text-white transition-all hover:bg-neutral-700 active:scale-[0.98]"
              style={{
                border: "1px solid #404040",
                background: "#1a1a1a",
                padding: "16px 24px",
                fontFamily: "monospace",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M17.64 9.20454C17.64 8.56636 17.5827 7.95272 17.4764 7.36363H9V10.845H13.8436C13.635 11.97 13.0009 12.9232 12.0477 13.5614V15.8195H14.9564C16.6582 14.2527 17.64 11.9455 17.64 9.20454Z" fill="#4285F4"/>
                <path d="M9 18C11.43 18 13.4673 17.1941 14.9564 15.8195L12.0477 13.5614C11.2418 14.1014 10.2109 14.4205 9 14.4205C6.65591 14.4205 4.67182 12.8373 3.96409 10.71H0.957275V13.0418C2.43818 15.9832 5.48182 18 9 18Z" fill="#34A853"/>
                <path d="M3.96409 10.71C3.78409 10.17 3.68182 9.59318 3.68182 9C3.68182 8.40682 3.78409 7.83 3.96409 7.29V4.95818H0.957275C0.347727 6.17318 0 7.54773 0 9C0 10.4523 0.347727 11.8268 0.957275 13.0418L3.96409 10.71Z" fill="#FBBC05"/>
                <path d="M9 3.57955C10.3214 3.57955 11.5077 4.03364 12.4405 4.92545L15.0218 2.34409C13.4632 0.891818 11.4259 0 9 0C5.48182 0 2.43818 2.01682 0.957275 4.95818L3.96409 7.29C4.67182 5.16273 6.65591 3.57955 9 3.57955Z" fill="#EA4335"/>
              </svg>
              Continue with Google
            </a>

            <div className="mt-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-neutral-800" />
              <span className="text-[10px] uppercase tracking-wider text-neutral-600" style={{ fontFamily: "monospace" }}>secure login</span>
              <div className="h-px flex-1 bg-neutral-800" />
            </div>

            <div className="mt-5 grid grid-cols-3 gap-3">
              {[
                { icon: <Shield size={16} />, label: "TEE Secured" },
                { icon: <Globe size={16} />, label: "On-chain" },
                { icon: <Zap size={16} />, label: "Non-custodial" },
              ].map((b, i) => (
                <div key={i} className="flex flex-col items-center gap-2 rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
                  <span className="text-[#CC5A38]">{b.icon}</span>
                  <span className="text-xs text-neutral-400 text-center" style={{ fontFamily: "monospace" }}>{b.label}</span>
                </div>
              ))}
            </div>

            <p className="mt-8 text-center text-[11px] text-neutral-600 leading-relaxed" style={{ fontFamily: "monospace" }}>
              By signing in, you agree that your agent wallets are managed inside
              Trusted Execution Environments. Your keys never leave the TEE.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
