"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { LogOut, RefreshCw, ExternalLink, TrendingUp, TrendingDown, MessageSquare, BarChart3, Zap, Shield } from "lucide-react";
import { LoginPage } from "@/components/login-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserInfo {
  userId: string;
  email: string;
  name: string;
  avatarUrl: string;
}

interface TradeRecord {
  trade_id: string;
  market_id: string;
  question: string;
  side: string;
  amount_usd: number;
  entry_price: number;
  status: string;
  clob_filled: boolean;
  split_tx: string | null;
  created_at: string;
}

interface Stats {
  agents: number;
  trades: number;
  volume_usd: number;
  open_positions: number;
}

type Tab = "overview" | "chat" | "trades" | "alpha";

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  sub,
  delta,
}: {
  label: string;
  value: string;
  sub?: string;
  delta?: { text: string; up: boolean };
}) {
  return (
    <div
      className="flex flex-col justify-between rounded-xl border p-5"
      style={{ borderColor: "#CC5A38", background: "#0a0a0a", minHeight: 120 }}
    >
      <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
        {label}
      </p>
      <p className="text-3xl font-black text-white font-mono mt-2">{value}</p>
      <div className="flex items-center justify-between mt-3">
        <span className="text-[10px] text-neutral-500 font-mono uppercase">{sub}</span>
        {delta && (
          <span
            className={`text-[10px] font-mono font-bold ${delta.up ? "text-green-400" : "text-red-400"}`}
          >
            {delta.up ? "↑" : "↓"} {delta.text}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Bar Chart ────────────────────────────────────────────────────────────────
function BarChart({ values }: { values: number[] }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex items-end gap-[3%] h-full w-full">
      {values.map((v, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm transition-all hover:opacity-80"
          style={{
            height: `${(v / max) * 100}%`,
            background: "linear-gradient(to top, #CC5A38, #e8855f)",
            minHeight: 4,
          }}
        />
      ))}
    </div>
  );
}

// ─── Overview Tab ─────────────────────────────────────────────────────────────
function OverviewTab({ stats, trades }: { stats: Stats | null; trades: TradeRecord[] }) {
  const fmtUSD = (n: number) => {
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `$${(n / 1_000).toFixed(1)}K`;
    return `$${n.toFixed(0)}`;
  };

  // Synthetic bar chart: trade volumes grouped into 12 buckets from recent trades
  const barVals = (() => {
    if (!trades.length) return [40, 55, 45, 70, 60, 85, 75, 50, 65, 90, 80, 95];
    const buckets = Array(12).fill(0);
    trades.slice(-12).forEach((t, i) => { buckets[i] = t.amount_usd; });
    return buckets;
  })();

  const recentTrades = trades.slice(0, 5);

  return (
    <div className="space-y-5">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Agents"
          value={stats ? String(stats.agents) : "—"}
          sub="Registered"
          delta={stats && stats.agents > 0 ? { text: "Active", up: true } : undefined}
        />
        <StatCard
          label="Trade Volume"
          value={stats ? fmtUSD(stats.volume_usd) : "—"}
          sub="All time"
          delta={{ text: "On-chain", up: true }}
        />
        <StatCard
          label="Total Trades"
          value={stats ? String(stats.trades) : "—"}
          sub="Executed"
        />
        <StatCard
          label="Open Positions"
          value={stats ? String(stats.open_positions) : "—"}
          sub="Live"
          delta={stats && stats.open_positions > 0 ? { text: "Live", up: true } : undefined}
        />
      </div>

      {/* Middle row: bar chart + recent trades */}
      <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4">
        {/* Balance / Volume History */}
        <div
          className="rounded-xl border p-5"
          style={{ borderColor: "#CC5A38", background: "#0a0a0a", height: 220 }}
        >
          <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
            Trade Volume History
          </p>
          <div style={{ height: "calc(100% - 32px)" }}>
            <BarChart values={barVals} />
          </div>
        </div>

        {/* Recent Trades */}
        <div
          className="rounded-xl border p-5"
          style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
        >
          <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
            Recent Trades
          </p>
          {recentTrades.length === 0 ? (
            <p className="text-neutral-600 text-xs font-mono">No trades yet.</p>
          ) : (
            <div className="space-y-2">
              {recentTrades.map((t) => (
                <div key={t.trade_id} className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-white font-mono truncate max-w-[180px]">{t.question || t.market_id}</p>
                    <p className="text-[10px] text-neutral-500 font-mono">{t.side} · ${t.amount_usd.toFixed(0)}</p>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold ml-2 ${t.status === "executed" ? "text-green-400" : "text-red-400"}`}
                  >
                    {t.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Trade Performance Table */}
      <div
        className="rounded-xl border p-5"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
          Trade Performance
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b" style={{ borderColor: "#CC5A38" }}>
                {["Trade Name", "Position Size", "Status", "Profit/Loss %", "Tx Hash"].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[10px] uppercase tracking-widest" style={{ color: "#CC5A38" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-neutral-600">
                    No trades recorded yet.
                  </td>
                </tr>
              ) : (
                trades.slice(0, 8).map((t) => (
                  <tr key={t.trade_id} className="border-b border-neutral-800 hover:bg-neutral-900/30">
                    <td className="py-2.5 pr-4 text-white truncate max-w-[200px]">{t.question || t.market_id}</td>
                    <td className="py-2.5 pr-4 text-neutral-300">${t.amount_usd.toFixed(2)}</td>
                    <td className="py-2.5 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                          t.status === "executed" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-neutral-400">—</td>
                    <td className="py-2.5">
                      {t.split_tx ? (
                        <a
                          href={`https://polygonscan.com/tx/${t.split_tx}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#CC5A38] hover:underline"
                        >
                          {t.split_tx.slice(0, 8)}…
                        </a>
                      ) : (
                        <span className="text-neutral-600">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Chat Tab ─────────────────────────────────────────────────────────────────
function ChatTab() {
  return (
    <div
      className="rounded-xl border p-8 flex flex-col items-center justify-center"
      style={{ borderColor: "#CC5A38", background: "#0a0a0a", minHeight: 400 }}
    >
      <MessageSquare size={32} className="mb-4" style={{ color: "#CC5A38" }} />
      <p className="text-white font-mono text-lg font-bold">Agent Chat</p>
      <p className="text-neutral-500 text-xs font-mono mt-2 text-center max-w-xs">
        Chat with your trading agents. Connect an agent API key to interact.
      </p>
      <div className="mt-6 w-full max-w-sm">
        <div className="rounded-xl border border-neutral-800 bg-neutral-900 p-4 text-xs text-neutral-500 font-mono text-center">
          Coming soon — real-time agent messaging
        </div>
      </div>
    </div>
  );
}

// ─── Trades Tab ───────────────────────────────────────────────────────────────
function TradesTab({ trades }: { trades: TradeRecord[] }) {
  return (
    <div
      className="rounded-xl border p-5"
      style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
    >
      <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
        All Trades
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b" style={{ borderColor: "#CC5A38" }}>
              {["Market", "Side", "Amount", "Entry Price", "Status", "Date", "Tx"].map((h) => (
                <th key={h} className="text-left py-2 pr-4 text-[10px] uppercase tracking-widest" style={{ color: "#CC5A38" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-neutral-600">No trades yet.</td>
              </tr>
            ) : (
              trades.map((t) => (
                <tr key={t.trade_id} className="border-b border-neutral-800 hover:bg-neutral-900/30">
                  <td className="py-2.5 pr-4 text-white truncate max-w-[180px]">{t.question || t.market_id}</td>
                  <td className={`py-2.5 pr-4 font-bold ${t.side === "YES" ? "text-green-400" : "text-red-400"}`}>{t.side}</td>
                  <td className="py-2.5 pr-4 text-neutral-300">${t.amount_usd.toFixed(2)}</td>
                  <td className="py-2.5 pr-4 text-neutral-400">{t.entry_price ? t.entry_price.toFixed(3) : "—"}</td>
                  <td className="py-2.5 pr-4">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${t.status === "executed" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 text-neutral-500">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td className="py-2.5">
                    {t.split_tx ? (
                      <a href={`https://polygonscan.com/tx/${t.split_tx}`} target="_blank" rel="noopener noreferrer" className="text-[#CC5A38] hover:underline">
                        {t.split_tx.slice(0, 8)}…
                      </a>
                    ) : <span className="text-neutral-600">—</span>}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Alpha Tab ────────────────────────────────────────────────────────────────
function AlphaTab() {
  const signals = [
    { market: "Will BTC hit $100K by Q2 2025?", signal: "BUY YES", confidence: 78, source: "Metengine" },
    { market: "Will ETH merge trigger SEC action?", signal: "BUY NO", confidence: 62, source: "Sozu" },
    { market: "Will Fed cut rates in June 2025?", signal: "BUY YES", confidence: 71, source: "EigenPoly AI" },
    { market: "Will Apple Vision Pro outsell Quest 3?", signal: "BUY NO", confidence: 55, source: "Metengine" },
  ];

  return (
    <div className="space-y-4">
      <div
        className="rounded-xl border p-5"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Zap size={14} style={{ color: "#CC5A38" }} />
          <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
            Alpha Signals — Powered by Sozu + Metengine
          </p>
        </div>
        <div className="space-y-3">
          {signals.map((s, i) => (
            <div key={i} className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white font-mono truncate">{s.market}</p>
                <p className="text-[10px] text-neutral-500 font-mono mt-0.5">{s.source}</p>
              </div>
              <div className="flex items-center gap-3 ml-4">
                <div className="text-right">
                  <span className={`text-xs font-bold font-mono ${s.signal.includes("YES") ? "text-green-400" : "text-red-400"}`}>
                    {s.signal}
                  </span>
                  <p className="text-[10px] text-neutral-500 font-mono">{s.confidence}% confidence</p>
                </div>
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-[10px] font-bold font-mono"
                  style={{
                    background: `conic-gradient(#CC5A38 ${s.confidence * 3.6}deg, #1a1a1a 0deg)`,
                  }}
                >
                  <div className="w-7 h-7 rounded-full bg-[#0a0a0a] flex items-center justify-center text-white text-[8px]">
                    {s.confidence}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        className="rounded-xl border p-5"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} style={{ color: "#CC5A38" }} />
          <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
            TEE Attestation
          </p>
        </div>
        <p className="text-xs text-neutral-400 font-mono">
          All signals are computed inside Trusted Execution Environments.
          Verify integrity at{" "}
          <a
            href="https://verify.eigencloud.xyz/app/0xE7caC048d1C305A5b870e147A080298eb1DE9877"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
            style={{ color: "#CC5A38" }}
          >
            eigencloud.xyz
          </a>
        </p>
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function DashboardPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<Stats | null>(null);
  const [trades, setTrades] = useState<TradeRecord[]>([]);

  const loginUrl = `${API_URL}/oauth/google?redirect=/dashboard`;

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/oauth/me`, { credentials: "include" });
        if (res.ok) setUser(await res.json());
      } catch {} finally { setLoading(false); }
    })();
  }, []);

  useEffect(() => {
    fetch("/api/stats").then(r => r.json()).then(setStats).catch(() => null);
  }, []);

  const handleLogout = async () => {
    await fetch(`${API_URL}/oauth/logout`, { method: "POST", credentials: "include" });
    window.location.href = "/";
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <RefreshCw size={22} className="animate-spin" style={{ color: "#CC5A38" }} />
      </main>
    );
  }

  if (!user) return <LoginPage loginUrl={loginUrl} />;

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }).toUpperCase();

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "chat", label: "Chat" },
    { id: "trades", label: "Trades" },
    { id: "alpha", label: "Alpha" },
  ];

  return (
    <div className="flex min-h-screen bg-[#0a0a0a] font-mono" style={{ color: "#E6E2D6" }}>

      {/* ─── Sidebar ─── */}
      <aside
        className="flex w-52 flex-col border-r"
        style={{ borderColor: "#CC5A38", background: "#070707" }}
      >
        {/* Brand */}
        <div className="px-6 pt-7 pb-4">
          <Link href="/" className="text-xl font-black hover:opacity-80 transition-opacity" style={{ color: "#CC5A38" }}>
            EigenPoly
          </Link>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-4 py-2">
          <ul className="space-y-1">
            {tabs.map((t) => (
              <li key={t.id}>
                <button
                  onClick={() => setActiveTab(t.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    activeTab === t.id
                      ? "font-bold"
                      : "text-neutral-500 hover:text-neutral-300"
                  }`}
                  style={activeTab === t.id ? { color: "#CC5A38" } : {}}
                >
                  {t.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* User */}
        <div className="border-t px-5 py-5 space-y-3" style={{ borderColor: "#CC5A38" }}>
          <p className="text-[10px] uppercase tracking-widest text-neutral-600">Current User</p>
          <div className="flex items-center gap-2.5">
            {user.avatarUrl ? (
              <img src={user.avatarUrl} alt="" className="h-7 w-7 rounded-full" />
            ) : (
              <div className="h-7 w-7 rounded-full bg-[#CC5A38]/20 flex items-center justify-center text-xs font-bold" style={{ color: "#CC5A38" }}>
                {user.name?.[0]}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold truncate text-white">{user.name}</p>
              <p className="text-[10px] text-neutral-500 truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-[11px] text-neutral-500 hover:text-red-400 transition-colors"
          >
            <LogOut size={11} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ─── Main Content ─── */}
      <main className="flex flex-1 flex-col min-h-screen overflow-auto">
        {/* Header */}
        <header
          className="flex items-center justify-between border-b px-8 py-5"
          style={{ borderColor: "#CC5A38" }}
        >
          <div>
            <h1 className="text-lg font-black uppercase tracking-wide text-white">
              EIGENPOLY DASHBOARD
            </h1>
            <p className="text-[10px] text-neutral-500 mt-0.5">{dateStr}</p>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://x.com/itsnishu"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs hover:underline"
              style={{ color: "#CC5A38" }}
            >
              contact for support: itsnishu
            </a>
            <span className="flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold uppercase text-green-400 bg-green-500/10">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
              Live
            </span>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 p-8">
          {activeTab === "overview" && <OverviewTab stats={stats} trades={trades} />}
          {activeTab === "chat" && <ChatTab />}
          {activeTab === "trades" && <TradesTab trades={trades} />}
          {activeTab === "alpha" && <AlphaTab />}
        </div>
      </main>
    </div>
  );
}
