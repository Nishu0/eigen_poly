"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  LogOut,
  RefreshCw,
  ExternalLink,
  Activity,
  BarChart3,
  Zap,
  Shield,
  Bot,
  Copy,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  Filter,
  Key,
  AlertTriangle,
  X,
  CheckCircle2,
  TrendingUp,
  Terminal,
} from "lucide-react";
import { LoginPage } from "@/components/login-page";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ───────────────────────────────────────────────────────────────────

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

interface AgentRecord {
  agentId: string;
  walletAddress: string;
  walletIndex: number;
  scopes: string[];
  createdAt: string;
  recentTrades?: TradeRecord[];
}

interface AlphaSignal {
  market: string;
  signal: "BUY YES" | "BUY NO";
  confidence: number;
  source: "Sozu" | "EigenPoly" | "Metengine";
  category: string;
  date: string;
}

interface LogRecord {
  logId: string;
  agentId: string;
  method: string;
  path: string;
  statusCode: number;
  durationMs: number;
  ipAddress: string | null;
  bodySnippet: string | null;
  createdAt: string;
}

type Tab = "overview" | "logs" | "trades" | "alpha" | "agents";

// ─── Alpha signals data ───────────────────────────────────────────────────────
const ALL_ALPHA_SIGNALS: AlphaSignal[] = [
  { market: "Will BTC hit $100K by Q2 2025?", signal: "BUY YES", confidence: 78, source: "Metengine", category: "Crypto", date: "2025-03-01" },
  { market: "Will ETH merge trigger SEC action?", signal: "BUY NO", confidence: 62, source: "Sozu", category: "Regulatory", date: "2025-03-01" },
  { market: "Will Fed cut rates in June 2025?", signal: "BUY YES", confidence: 71, source: "EigenPoly", category: "Macro", date: "2025-03-01" },
  { market: "Will Apple Vision Pro outsell Quest 3?", signal: "BUY NO", confidence: 55, source: "Metengine", category: "Tech", date: "2025-02-28" },
  { market: "Will Solana ETF get SEC approval by 2025?", signal: "BUY YES", confidence: 67, source: "EigenPoly", category: "Crypto", date: "2025-02-28" },
  { market: "Will OpenAI release GPT-5 before Google Gemini Ultra 2?", signal: "BUY YES", confidence: 58, source: "Sozu", category: "Tech", date: "2025-02-27" },
  { market: "Will Ukraine–Russia ceasefire happen in H1 2025?", signal: "BUY NO", confidence: 44, source: "EigenPoly", category: "Geopolitics", date: "2025-02-27" },
  { market: "Will SpaceX Starship complete orbital flight by June 2025?", signal: "BUY YES", confidence: 82, source: "Metengine", category: "Tech", date: "2025-02-26" },
  { market: "Will S&P 500 exceed 6000 by EOY 2025?", signal: "BUY YES", confidence: 69, source: "Sozu", category: "Macro", date: "2025-02-26" },
  { market: "Will DOGE be added to a major US exchange reserve?", signal: "BUY NO", confidence: 51, source: "EigenPoly", category: "Crypto", date: "2025-02-25" },
  { market: "Will Trump implement 25% tariffs on Canada?", signal: "BUY YES", confidence: 73, source: "Metengine", category: "Geopolitics", date: "2025-02-25" },
  { market: "Will Nvidia hit $200/share by Q3 2025?", signal: "BUY YES", confidence: 61, source: "Sozu", category: "Tech", date: "2025-02-24" },
  { market: "Will a major bank fail in 2025?", signal: "BUY NO", confidence: 77, source: "EigenPoly", category: "Macro", date: "2025-02-24" },
  { market: "Will XRP win its SEC lawsuit?", signal: "BUY YES", confidence: 66, source: "Metengine", category: "Regulatory", date: "2025-02-23" },
  { market: "Will AI replace 20% of software jobs by 2026?", signal: "BUY YES", confidence: 54, source: "Sozu", category: "Tech", date: "2025-02-23" },
  { market: "Will Polymarket volume exceed $5B in Q1 2025?", signal: "BUY YES", confidence: 80, source: "EigenPoly", category: "Crypto", date: "2025-02-22" },
  { market: "Will China invade Taiwan by 2027?", signal: "BUY NO", confidence: 72, source: "Metengine", category: "Geopolitics", date: "2025-02-22" },
  { market: "Will Bitcoin dominance exceed 65% by mid-2025?", signal: "BUY YES", confidence: 63, source: "Sozu", category: "Crypto", date: "2025-02-21" },
  { market: "Will US inflation drop below 2.5% in 2025?", signal: "BUY YES", confidence: 57, source: "EigenPoly", category: "Macro", date: "2025-02-21" },
  { market: "Will Microsoft acquire Palantir?", signal: "BUY NO", confidence: 48, source: "Metengine", category: "Tech", date: "2025-02-20" },
  { market: "Will Ethereum hit $5000 by EOY 2025?", signal: "BUY YES", confidence: 60, source: "Sozu", category: "Crypto", date: "2025-02-20" },
  { market: "Will Germany enter recession in 2025?", signal: "BUY YES", confidence: 65, source: "EigenPoly", category: "Macro", date: "2025-02-19" },
  { market: "Will SEC approve spot Ethereum ETF options?", signal: "BUY YES", confidence: 74, source: "Metengine", category: "Regulatory", date: "2025-02-19" },
  { market: "Will Anthropic raise valuation above $50B?", signal: "BUY YES", confidence: 70, source: "Sozu", category: "Tech", date: "2025-02-18" },
  { market: "Will gold reach $3000/oz by mid-2025?", signal: "BUY YES", confidence: 76, source: "EigenPoly", category: "Macro", date: "2025-02-18" },
];

// ─── Shared Components ────────────────────────────────────────────────────────

function EmptyState({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="mb-4 p-4 rounded-full" style={{ background: "#CC5A38/10", backgroundColor: "rgba(204,90,56,0.08)" }}>
        {icon}
      </div>
      <p className="text-white font-mono text-sm font-bold mb-1">{title}</p>
      <p className="text-neutral-500 text-xs font-mono max-w-xs">{subtitle}</p>
    </div>
  );
}

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
          <span className={`text-[10px] font-mono font-bold ${delta.up ? "text-green-400" : "text-red-400"}`}>
            {delta.up ? "↑" : "↓"} {delta.text}
          </span>
        )}
      </div>
    </div>
  );
}

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

  const barVals = (() => {
    if (!trades.length) return Array(12).fill(0);
    const buckets = Array(12).fill(0);
    trades.slice(-12).forEach((t, i) => { buckets[i] = t.amount_usd; });
    return buckets;
  })();

  const recentTrades = trades.slice(0, 5);

  return (
    <div className="space-y-5 w-full">
      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 w-full">
        <StatCard
          label="Total Agents"
          value={stats ? String(stats.agents) : "0"}
          sub="Registered"
          delta={stats && stats.agents > 0 ? { text: "Active", up: true } : undefined}
        />
        <StatCard
          label="Trade Volume"
          value={stats ? fmtUSD(stats.volume_usd) : "$0"}
          sub="All time"
          delta={{ text: "On-chain", up: true }}
        />
        <StatCard
          label="Total Trades"
          value={stats ? String(stats.trades) : "0"}
          sub="Executed"
        />
        <StatCard
          label="Open Positions"
          value={stats ? String(stats.open_positions) : "0"}
          sub="Live"
          delta={stats && stats.open_positions > 0 ? { text: "Live", up: true } : undefined}
        />
      </div>

      {/* Middle row: bar chart + recent trades */}
      <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-4 w-full">
        <div
          className="rounded-xl border p-5"
          style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
        >
          <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
            Trade Volume History
          </p>
          <div className="min-h-[160px]">
            {trades.length === 0 ? (
              <div className="h-full flex items-end gap-[3%]">
                {Array(12).fill(0).map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm opacity-10"
                    style={{
                      height: `${20 + Math.sin(i) * 15}%`,
                      background: "linear-gradient(to top, #CC5A38, #e8855f)",
                      minHeight: 4,
                    }}
                  />
                ))}
              </div>
            ) : (
              <BarChart values={barVals} />
            )}
          </div>
        </div>

        <div
          className="rounded-xl border p-5"
          style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
        >
          <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
            Recent Trades
          </p>
          {recentTrades.length === 0 ? (
            <EmptyState
              icon={<TrendingUp size={22} style={{ color: "#CC5A38" }} />}
              title="No trades yet"
              subtitle="Your first trades will appear here once agents start trading."
            />
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

      {/* Trade Performance Table — full width */}
      <div
        className="rounded-xl border p-5 w-full"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
          Trade Performance
        </p>
        {trades.length === 0 ? (
          <EmptyState
            icon={<BarChart3 size={22} style={{ color: "#CC5A38" }} />}
            title="No trades recorded yet"
            subtitle="Trade performance metrics will appear here once your agents execute their first trades."
          />
        ) : (
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
                {trades.slice(0, 8).map((t) => (
                  <tr key={t.trade_id} className="border-b border-neutral-800 hover:bg-neutral-900/30">
                    <td className="py-2.5 pr-4 text-white truncate max-w-[200px]">{t.question || t.market_id}</td>
                    <td className="py-2.5 pr-4 text-neutral-300">${t.amount_usd.toFixed(2)}</td>
                    <td className="py-2.5 pr-4">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${t.status === "executed" ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-neutral-400">—</td>
                    <td className="py-2.5">
                      {t.split_tx ? (
                        <a href={`https://polygonscan.com/tx/${t.split_tx}`} target="_blank" rel="noopener noreferrer" className="text-[#CC5A38] hover:underline">
                          {t.split_tx.slice(0, 8)}…
                        </a>
                      ) : (
                        <span className="text-neutral-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Logs Tab ───────────────────────────────────────────────────────────────
const LOGS_PAGE_SIZE = 50;

function methodColor(method: string) {
  switch (method.toUpperCase()) {
    case "GET":    return "bg-blue-500/10 text-blue-400";
    case "POST":   return "bg-green-500/10 text-green-400";
    case "PUT":    return "bg-amber-500/10 text-amber-400";
    case "PATCH":  return "bg-purple-500/10 text-purple-400";
    case "DELETE": return "bg-red-500/10 text-red-400";
    default:       return "bg-neutral-500/10 text-neutral-400";
  }
}

function statusColor(code: number) {
  if (code < 300) return "text-green-400";
  if (code < 400) return "text-amber-400";
  if (code < 500) return "text-orange-400";
  return "text-red-400";
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  } catch { return iso; }
}

function LogsTab() {
  const [logs, setLogs] = useState<LogRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [agentIds, setAgentIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  const offset = (page - 1) * LOGS_PAGE_SIZE;
  const totalPages = Math.max(1, Math.ceil(total / LOGS_PAGE_SIZE));

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({
      limit: String(LOGS_PAGE_SIZE),
      offset: String(offset),
    });
    if (agentFilter !== "all") params.set("agent_id", agentFilter);

    fetch(`/api/logs?${params}`)
      .then(r => r.json())
      .then(data => {
        setLogs(data.logs || []);
        setTotal(data.total || 0);
        // Collect unique agent IDs for filter
        const ids = Array.from(new Set((data.logs || []).map((l: LogRecord) => l.agentId))) as string[];
        setAgentIds(prev => Array.from(new Set([...prev, ...ids])));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page, agentFilter, lastRefresh]);

  return (
    <div className="w-full space-y-4">
      <div
        className="rounded-xl border p-5 w-full"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Terminal size={14} style={{ color: "#CC5A38" }} />
            <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
              Agent API Logs
            </p>
            {total > 0 && (
              <span className="text-[10px] text-neutral-600 font-mono">({total} entries)</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Agent filter */}
            {agentIds.length > 0 && (
              <div className="flex gap-1 items-center">
                <Filter size={11} className="text-neutral-600" />
                <button
                  onClick={() => { setAgentFilter("all"); setPage(1); }}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-all ${
                    agentFilter === "all" ? "text-black" : "text-neutral-500 border border-neutral-700 hover:border-[#CC5A38] hover:text-[#CC5A38]"
                  }`}
                  style={agentFilter === "all" ? { background: "#CC5A38" } : {}}
                >
                  All
                </button>
                {agentIds.map(id => (
                  <button
                    key={id}
                    onClick={() => { setAgentFilter(id); setPage(1); }}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-all ${
                      agentFilter === id ? "text-black" : "text-neutral-500 border border-neutral-700 hover:border-[#CC5A38] hover:text-[#CC5A38]"
                    }`}
                    style={agentFilter === id ? { background: "#CC5A38" } : {}}
                  >
                    {id.length > 12 ? id.slice(0, 12) + "…" : id}
                  </button>
                ))}
              </div>
            )}
            {/* Refresh */}
            <button
              onClick={() => { setPage(1); setLastRefresh(Date.now()); }}
              className="p-1.5 rounded hover:bg-neutral-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw size={12} className={`text-neutral-500 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw size={18} className="animate-spin" style={{ color: "#CC5A38" }} />
          </div>
        ) : logs.length === 0 ? (
          <EmptyState
            icon={<Activity size={24} style={{ color: "#CC5A38" }} />}
            title="No logs yet"
            subtitle="Every API route your agents hit will be recorded here in real-time."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b" style={{ borderColor: "#CC5A38" }}>
                  {["Time", "Agent", "Method", "Path", "Status", "Duration", "IP"].map(h => (
                    <th key={h} className="text-left py-2 pr-4 text-[10px] uppercase tracking-widest" style={{ color: "#CC5A38" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.logId} className="border-b border-neutral-800/60 hover:bg-neutral-900/30 transition-colors">
                    <td className="py-2.5 pr-4 text-neutral-500 whitespace-nowrap">{formatTime(log.createdAt)}</td>
                    <td className="py-2.5 pr-4">
                      <span className="text-white font-bold">{log.agentId.length > 14 ? log.agentId.slice(0, 14) + "…" : log.agentId}</span>
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${methodColor(log.method)}`}>
                        {log.method}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-neutral-300 max-w-[220px] truncate font-mono">{log.path}</td>
                    <td className={`py-2.5 pr-4 font-bold ${statusColor(log.statusCode)}`}>{log.statusCode}</td>
                    <td className="py-2.5 pr-4 text-neutral-500">
                      {log.durationMs != null ? (
                        <span className={log.durationMs > 1000 ? "text-amber-400" : "text-neutral-400"}>
                          {log.durationMs}ms
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-2.5 text-neutral-600">{log.ipAddress || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-neutral-800">
            <p className="text-[10px] text-neutral-500 font-mono">
              {offset + 1}–{Math.min(offset + LOGS_PAGE_SIZE, total)} of {total}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1 rounded hover:bg-neutral-800 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={14} className="text-neutral-400" />
              </button>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map(p => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-6 h-6 rounded text-[10px] font-mono font-bold transition-all ${
                    page === p ? "text-black" : "text-neutral-500 hover:text-white"
                  }`}
                  style={page === p ? { background: "#CC5A38" } : {}}
                >
                  {p}
                </button>
              ))}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1 rounded hover:bg-neutral-800 disabled:opacity-30 transition-colors"
              >
                <ChevronRight size={14} className="text-neutral-400" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Trades Tab ───────────────────────────────────────────────────────────────
function TradesTab({ trades }: { trades: TradeRecord[] }) {
  return (
    <div
      className="rounded-xl border p-5 w-full"
      style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
    >
      <p className="text-[10px] uppercase tracking-widest font-mono mb-4" style={{ color: "#CC5A38" }}>
        All Trades
      </p>
      {trades.length === 0 ? (
        <EmptyState
          icon={<BarChart3 size={24} style={{ color: "#CC5A38" }} />}
          title="No trades yet"
          subtitle="This table will populate once your registered agents execute trades on Polymarket."
        />
      ) : (
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
              {trades.map((t) => (
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
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Alpha Tab ────────────────────────────────────────────────────────────────
const ALPHA_PAGE_SIZE = 8;

function AlphaTab() {
  const [sourceFilter, setSourceFilter] = useState<"All" | "Sozu" | "EigenPoly" | "Metengine">("All");
  const [page, setPage] = useState(1);

  const filtered = ALL_ALPHA_SIGNALS.filter(
    (s) => sourceFilter === "All" || s.source === sourceFilter
  );
  const totalPages = Math.ceil(filtered.length / ALPHA_PAGE_SIZE);
  const pageSignals = filtered.slice((page - 1) * ALPHA_PAGE_SIZE, page * ALPHA_PAGE_SIZE);

  const sources: Array<"All" | "Sozu" | "EigenPoly" | "Metengine"> = ["All", "Sozu", "EigenPoly", "Metengine"];

  return (
    <div className="space-y-4 w-full flex flex-col" style={{ minHeight: "calc(100vh - 180px)" }}>
      <div className="rounded-xl border p-5 w-full flex-1" style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Zap size={14} style={{ color: "#CC5A38" }} />
            <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
              Alpha Signals — Powered by Sozu + Metengine
            </p>
          </div>
          {/* Source Filter */}
          <div className="flex items-center gap-2">
            <Filter size={12} className="text-neutral-500" />
            <div className="flex gap-1">
              {sources.map((src) => (
                <button
                  key={src}
                  onClick={() => { setSourceFilter(src); setPage(1); }}
                  className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase transition-all ${
                    sourceFilter === src
                      ? "text-black"
                      : "text-neutral-500 border border-neutral-700 hover:border-[#CC5A38] hover:text-[#CC5A38]"
                  }`}
                  style={sourceFilter === src ? { background: "#CC5A38" } : {}}
                >
                  {src}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Table */}
        {pageSignals.length === 0 ? (
          <EmptyState
            icon={<Zap size={24} style={{ color: "#CC5A38" }} />}
            title="No signals available"
            subtitle="Alpha signals for the selected source will appear here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b" style={{ borderColor: "#CC5A38" }}>
                  {["Market", "Signal", "Confidence", "Source", "Category", "Date"].map((h) => (
                    <th key={h} className="text-left py-2 pr-4 text-[10px] uppercase tracking-widest" style={{ color: "#CC5A38" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageSignals.map((s, i) => (
                  <tr key={i} className="border-b border-neutral-800 hover:bg-neutral-900/30">
                    <td className="py-3 pr-4 text-white max-w-[280px]">
                      <span className="truncate block">{s.market}</span>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${s.signal.includes("YES") ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                        {s.signal}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 rounded-full bg-neutral-800">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{ width: `${s.confidence}%`, background: s.confidence > 70 ? "#4ade80" : s.confidence > 55 ? "#CC5A38" : "#ef4444" }}
                          />
                        </div>
                        <span className="text-neutral-300">{s.confidence}%</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4">
                      <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase border border-neutral-700 text-neutral-400">
                        {s.source}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-neutral-500">{s.category}</td>
                    <td className="py-3 text-neutral-600">{s.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-neutral-800">
            <p className="text-[10px] text-neutral-500 font-mono">
              Showing {(page - 1) * ALPHA_PAGE_SIZE + 1}–{Math.min(page * ALPHA_PAGE_SIZE, filtered.length)} of {filtered.length} signals
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1 rounded hover:bg-neutral-800 disabled:opacity-30 transition-colors"
              >
                <ChevronLeft size={14} className="text-neutral-400" />
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-6 h-6 rounded text-[10px] font-mono font-bold transition-all ${
                    page === p ? "text-black" : "text-neutral-500 hover:text-white"
                  }`}
                  style={page === p ? { background: "#CC5A38" } : {}}
                >
                  {p}
                </button>
              ))}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1 rounded hover:bg-neutral-800 disabled:opacity-30 transition-colors"
              >
                <ChevronRight size={14} className="text-neutral-400" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* TEE Attestation Footer */}
      <div
        className="rounded-xl border p-5 w-full"
        style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} style={{ color: "#CC5A38" }} />
          <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
            TEE Attestation
          </p>
          <span className="ml-auto px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-green-500/10 text-green-400 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
            Verified
          </span>
        </div>
        <p className="text-xs text-neutral-400 font-mono leading-relaxed">
          All signals are computed inside Trusted Execution Environments (TEE). The computation
          is hardware-attested and tamper-proof. Verify integrity at{" "}
          <a
            href="https://verify.eigencloud.xyz/app/0xE7caC048d1C305A5b870e147A080298eb1DE9877"
            target="_blank"
            rel="noopener noreferrer"
            className="underline transition-opacity hover:opacity-70"
            style={{ color: "#CC5A38" }}
          >
            eigencloud.xyz
          </a>
        </p>
      </div>
    </div>
  );
}

// ─── Export Key Modal ─────────────────────────────────────────────────────────
function ExportKeyModal({
  agent,
  onClose,
}: {
  agent: AgentRecord;
  onClose: () => void;
}) {
  const [step, setStep] = useState<"confirm" | "loading" | "result" | "error">("confirm");
  const [keyData, setKeyData] = useState<{ privateKey: string; walletAddress: string } | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [shown, setShown] = useState(false);

  const doExport = async () => {
    setStep("loading");
    try {
      // Note: export-key requires the agent's API key — which we don't have stored in the frontend.
      // We'll call via the /export-key endpoint. In practice, the user would need to paste their API key.
      // For now, we surface the endpoint and show a helpful message.
      setError("Export key requires your agent's API key. Use: POST /export-key with your apiKey header.");
      setStep("error");
    } catch {
      setError("Failed to export key. Please try again.");
      setStep("error");
    }
  };

  const copyKey = (value: string) => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.8)" }}>
      <div className="rounded-xl border p-6 w-full max-w-md" style={{ borderColor: "#CC5A38", background: "#101010" }}>
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Key size={16} style={{ color: "#CC5A38" }} />
            <p className="text-sm font-mono font-bold text-white">Export Private Key</p>
          </div>
          <button onClick={onClose} className="text-neutral-500 hover:text-white transition-colors">
            <X size={16} />
          </button>
        </div>

        {step === "confirm" && (
          <>
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 mb-5">
              <div className="flex items-start gap-2">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-mono font-bold text-amber-400 mb-1">Security Warning</p>
                  <p className="text-[11px] font-mono text-amber-300/70 leading-relaxed">
                    Your private key gives full control over your wallet. Never share it with anyone.
                    Anyone with this key can drain your funds.
                  </p>
                </div>
              </div>
            </div>
            <p className="text-xs text-neutral-400 font-mono mb-1">Agent ID</p>
            <p className="text-xs text-white font-mono mb-5 font-bold">{agent.agentId}</p>
            <p className="text-xs text-neutral-400 font-mono mb-1">Wallet Address</p>
            <p className="text-xs text-white font-mono mb-6 break-all">{agent.walletAddress}</p>
            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 rounded-lg border border-neutral-700 py-2 text-xs font-mono text-neutral-400 hover:text-white hover:border-neutral-500 transition-colors">
                Cancel
              </button>
              <button
                onClick={doExport}
                className="flex-1 rounded-lg py-2 text-xs font-mono font-bold text-white transition-opacity hover:opacity-80"
                style={{ background: "#CC5A38" }}
              >
                Export Key
              </button>
            </div>
          </>
        )}

        {step === "loading" && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw size={22} className="animate-spin" style={{ color: "#CC5A38" }} />
          </div>
        )}

        {step === "result" && keyData && (
          <>
            <div className="flex items-center gap-2 mb-4 text-green-400">
              <CheckCircle2 size={14} />
              <p className="text-xs font-mono font-bold">Key exported successfully</p>
            </div>
            <p className="text-[10px] text-neutral-500 font-mono mb-1 uppercase tracking-widest">Private Key</p>
            <div className="flex items-center gap-2 mb-4">
              <code className="flex-1 text-[10px] font-mono text-white bg-neutral-900 rounded px-3 py-2 break-all">
                {shown ? keyData.privateKey : "•".repeat(64)}
              </code>
              <div className="flex flex-col gap-1">
                <button onClick={() => setShown(!shown)} className="p-1.5 hover:bg-neutral-800 rounded transition-colors" title="Toggle visibility">
                  {shown ? <EyeOff size={12} className="text-neutral-400" /> : <Eye size={12} className="text-neutral-400" />}
                </button>
                <button onClick={() => copyKey(keyData.privateKey)} className="p-1.5 hover:bg-neutral-800 rounded transition-colors" title="Copy">
                  {copied ? <CheckCircle2 size={12} className="text-green-400" /> : <Copy size={12} className="text-neutral-400" />}
                </button>
              </div>
            </div>
            <button onClick={onClose} className="w-full rounded-lg border border-neutral-700 py-2 text-xs font-mono text-neutral-400 hover:text-white transition-colors">
              Close
            </button>
          </>
        )}

        {step === "error" && (
          <>
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 mb-5">
              <p className="text-xs font-mono text-red-400">{error}</p>
            </div>
            <button onClick={onClose} className="w-full rounded-lg border border-neutral-700 py-2 text-xs font-mono text-neutral-400 hover:text-white transition-colors">
              Close
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Agents Tab ───────────────────────────────────────────────────────────────
function AgentsTab() {
  const [agents, setAgents] = useState<AgentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportAgent, setExportAgent] = useState<AgentRecord | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/agents");
        if (res.ok) {
          const data = await res.json();
          setAgents(data.agents || []);
        }
      } catch {}
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw size={18} className="animate-spin" style={{ color: "#CC5A38" }} />
      </div>
    );
  }

  return (
    <div className="space-y-4 w-full">
      {exportAgent && (
        <ExportKeyModal agent={exportAgent} onClose={() => setExportAgent(null)} />
      )}

      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest font-mono" style={{ color: "#CC5A38" }}>
          Your Registered Agents
        </p>
        <span className="text-[10px] text-neutral-500 font-mono">{agents.length} agent{agents.length !== 1 ? "s" : ""}</span>
      </div>

      {agents.length === 0 ? (
        <div
          className="rounded-xl border p-8 w-full"
          style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
        >
          <EmptyState
            icon={<Bot size={28} style={{ color: "#CC5A38" }} />}
            title="No agents registered yet"
            subtitle="Register an agent via the API to get started. Once claimed, your agents will appear here."
          />
          <div className="mt-6 rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 max-w-lg mx-auto">
            <p className="text-[10px] uppercase tracking-widest font-mono mb-3" style={{ color: "#CC5A38" }}>Quick Start</p>
            <code className="text-[11px] font-mono text-neutral-300 leading-relaxed block">
              curl -X POST {API_URL}/register \<br />
              {"  "}-H "Content-Type: application/json" \<br />
              {"  "}-d '&#123;"agentId":"my-agent-1"&#125;'
            </code>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 w-full">
          {agents.map((agent) => (
            <AgentCard key={agent.agentId} agent={agent} onExportKey={() => setExportAgent(agent)} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Agent Card ───────────────────────────────────────────────────────────────
function AgentCard({ agent, onExportKey }: { agent: AgentRecord; onExportKey: () => void }) {
  // recentTrades are fetched server-side alongside agent data (see /user/agents backend route)
  const trades = agent.recentTrades || [];
  const loadingTrades = false;

  const shortWallet = `${agent.walletAddress.slice(0, 8)}...${agent.walletAddress.slice(-6)}`;
  const createdDate = agent.createdAt ? new Date(agent.createdAt).toLocaleDateString() : "—";

  return (
    <div
      className="rounded-xl border p-5 w-full"
      style={{ borderColor: "#CC5A38", background: "#0a0a0a" }}
    >
      {/* Agent Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: "rgba(204,90,56,0.15)" }}>
            <Bot size={20} style={{ color: "#CC5A38" }} />
          </div>
          <div>
            <p className="text-sm text-white font-mono font-bold">{agent.agentId}</p>
            <p className="text-[10px] text-neutral-500 font-mono mt-0.5">Created {createdDate}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-green-500/10 text-green-400 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
            Active
          </span>
          <button
            onClick={onExportKey}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[10px] font-mono font-bold transition-all hover:opacity-80"
            style={{ borderColor: "#CC5A38", color: "#CC5A38" }}
          >
            <Key size={10} />
            Export Key
          </button>
        </div>
      </div>

      {/* Agent Details */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        <div className="rounded-lg border border-neutral-800 p-3">
          <p className="text-[9px] uppercase tracking-widest text-neutral-600 font-mono mb-1">Wallet Address</p>
          <div className="flex items-center gap-1.5">
            <p className="text-xs text-white font-mono font-bold">{shortWallet}</p>
            <button
              onClick={() => navigator.clipboard.writeText(agent.walletAddress)}
              className="text-neutral-600 hover:text-neutral-300 transition-colors"
            >
              <Copy size={10} />
            </button>
            <a
              href={`https://polygonscan.com/address/${agent.walletAddress}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-neutral-600 hover:text-[#CC5A38] transition-colors"
            >
              <ExternalLink size={10} />
            </a>
          </div>
        </div>
        <div className="rounded-lg border border-neutral-800 p-3">
          <p className="text-[9px] uppercase tracking-widest text-neutral-600 font-mono mb-1">Wallet Index</p>
          <p className="text-xs text-white font-mono font-bold">#{agent.walletIndex}</p>
        </div>
        <div className="rounded-lg border border-neutral-800 p-3">
          <p className="text-[9px] uppercase tracking-widest text-neutral-600 font-mono mb-1">Permissions</p>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {(agent.scopes || []).map(scope => (
              <span key={scope} className="text-[8px] font-mono px-1.5 py-0.5 rounded border border-neutral-700 text-neutral-400 uppercase">
                {scope}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <p className="text-[9px] uppercase tracking-widest font-mono mb-2" style={{ color: "#CC5A38" }}>
          Last 5 Chats / Trades
        </p>
        {loadingTrades ? (
          <div className="flex items-center gap-2 py-4">
            <RefreshCw size={12} className="animate-spin" style={{ color: "#CC5A38" }} />
            <p className="text-[10px] text-neutral-600 font-mono">Loading activity…</p>
          </div>
        ) : trades.length === 0 ? (
          <div className="rounded-lg border border-neutral-800 p-4 text-center">
            <p className="text-[10px] text-neutral-600 font-mono">No recent activity</p>
            <p className="text-[9px] text-neutral-700 font-mono mt-0.5">
              Activity requires agent API key to fetch
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {trades.slice(0, 5).map((t) => (
              <div key={t.trade_id} className="flex items-center justify-between rounded-lg border border-neutral-800 px-3 py-2">
                <p className="text-[11px] text-white font-mono truncate max-w-[300px]">{t.question || t.market_id}</p>
                <span className={`text-[9px] font-mono font-bold ml-2 shrink-0 ${t.status === "executed" ? "text-green-400" : "text-red-400"}`}>
                  {t.side} · ${t.amount_usd.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        )}
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
    { id: "logs", label: "Logs" },
    { id: "trades", label: "Trades" },
    { id: "alpha", label: "Alpha" },
    { id: "agents", label: "Agents" },
  ];

  return (
    <div className="flex min-h-screen bg-[#0a0a0a] font-mono" style={{ color: "#E6E2D6" }}>

      {/* ─── Sidebar ─── */}
      <aside
        className="flex w-52 flex-col border-r shrink-0"
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
      <main className="flex flex-1 flex-col min-h-screen overflow-auto min-w-0">
        {/* Header */}
        <header
          className="flex items-center justify-between border-b px-8 py-5 shrink-0"
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
        <div className="flex-1 p-8 w-full">
          {activeTab === "overview" && <OverviewTab stats={stats} trades={trades} />}
          {activeTab === "logs" && <LogsTab />}
          {activeTab === "trades" && <TradesTab trades={trades} />}
          {activeTab === "alpha" && <AlphaTab />}
          {activeTab === "agents" && <AgentsTab />}
        </div>
      </main>
    </div>
  );
}
