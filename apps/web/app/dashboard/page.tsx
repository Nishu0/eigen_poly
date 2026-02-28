"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Key,
  Wallet,
  Copy,
  Check,
  Eye,
  EyeOff,
  Shield,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Coins,
  LogOut,
  LayoutDashboard,
  Settings,
  ChevronRight,
  Plus,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface UserInfo {
  userId: string;
  email: string;
  name: string;
  avatarUrl: string;
}

interface AgentSummary {
  agentId: string;
  walletAddress: string;
  walletIndex: number;
  scopes: string[];
  createdAt: string;
}

interface BalanceData {
  eoa: { address: string; pol: number; usdc_e: number };
  safe: { address: string; pol: number; usdc_e: number };
  total_usdc_e: number;
  total_usd: number;
}

export default function DashboardPage() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentSummary | null>(null);
  const [balances, setBalances] = useState<BalanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [balanceLoading, setBalanceLoading] = useState(false);

  // Key export state
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [privateKey, setPrivateKey] = useState<string | null>(null);
  const [showPrivateKey, setShowPrivateKey] = useState(false);
  const [keyExportLoading, setKeyExportLoading] = useState(false);

  const [copied, setCopied] = useState<string | null>(null);

  const copyToClipboard = useCallback((text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  }, []);

  // Check session + load agents
  useEffect(() => {
    (async () => {
      try {
        const userRes = await fetch(`${API_URL}/oauth/me`, { credentials: "include" });
        if (!userRes.ok) {
          setLoading(false);
          return;
        }
        const userData = await userRes.json();
        setUser(userData);

        const agentRes = await fetch(`${API_URL}/user/agents`, { credentials: "include" });
        if (agentRes.ok) {
          const data = await agentRes.json();
          setAgents(data.agents || []);
          if (data.agents?.length > 0) setSelectedAgent(data.agents[0]);
        }
      } catch {} finally {
        setLoading(false);
      }
    })();
  }, []);

  // Load balance when agent is selected (needs API key)
  const loadBalance = async () => {
    if (!selectedAgent || !apiKeyInput) return;
    setBalanceLoading(true);
    try {
      const res = await fetch(`${API_URL}/balance/${selectedAgent.agentId}`, {
        headers: { "x-api-key": apiKeyInput },
      });
      if (res.ok) setBalances(await res.json());
    } catch {} finally {
      setBalanceLoading(false);
    }
  };

  const exportKey = async () => {
    if (!selectedAgent || !apiKeyInput) return;
    setKeyExportLoading(true);
    try {
      const res = await fetch(`${API_URL}/export-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-api-key": apiKeyInput },
        body: JSON.stringify({ agentId: selectedAgent.agentId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Export failed" }));
        throw new Error(err.detail);
      }
      const data = await res.json();
      setPrivateKey(data.privateKey);
    } catch (e: any) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setKeyExportLoading(false);
    }
  };

  const handleLogout = async () => {
    await fetch(`${API_URL}/oauth/logout`, { method: "POST", credentials: "include" });
    window.location.href = "/";
  };

  const truncateAddr = (addr: string) =>
    addr ? `${addr.slice(0, 6)}...${addr.slice(-4)}` : "";

  const loginUrl = `${API_URL}/oauth/google?redirect=/dashboard`;

  // ────── Loading ──────
  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white">
        <RefreshCw size={24} className="animate-spin text-neutral-400" />
      </main>
    );
  }

  // ────── Not logged in ──────
  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
        <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500/10">
            <Shield size={28} className="text-emerald-400" />
          </div>
          <h1 className="text-xl font-semibold">EigenPoly Dashboard</h1>
          <p className="mt-2 text-sm text-neutral-400">Sign in to manage your agents</p>
          <a
            href={loginUrl}
            className="mt-6 inline-flex items-center gap-3 rounded-lg border border-neutral-700 bg-neutral-800 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-neutral-700"
          >
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </a>
        </div>
      </main>
    );
  }

  // ────── Dashboard ──────
  return (
    <main className="flex min-h-screen bg-[#0A0A0A] text-white">
      {/* ─── Sidebar ─── */}
      <aside className="flex w-64 flex-col border-r border-neutral-800 bg-[#111111]">
        <div className="flex items-center gap-2 border-b border-neutral-800 px-5 py-4">
          <Shield size={20} className="text-emerald-400" />
          <span className="text-sm font-semibold">EigenPoly</span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          <div className="flex items-center gap-2 rounded-lg bg-neutral-800 px-3 py-2 text-sm font-medium">
            <LayoutDashboard size={16} className="text-emerald-400" />
            Agents
          </div>
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors"
          >
            <ExternalLink size={16} />
            API Docs
          </a>
          <a
            href="https://verify.eigencloud.xyz/app/0xE7caC048d1C305A5b870e147A080298eb1DE9877"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors"
          >
            <Shield size={16} />
            TEE Attestation
          </a>
        </nav>

        {/* User */}
        <div className="border-t border-neutral-800 p-4">
          <div className="flex items-center gap-3">
            {user.avatarUrl ? (
              <img src={user.avatarUrl} alt="" className="h-8 w-8 rounded-full" />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-semibold text-emerald-400">
                {user.name?.[0] || "?"}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium truncate">{user.name}</p>
              <p className="text-[10px] text-neutral-500 truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-3 flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={12} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ─── Main Content ─── */}
      <div className="flex-1 overflow-auto">
        {/* Header */}
        <header className="sticky top-0 z-10 border-b border-neutral-800 bg-[#0A0A0A]/80 backdrop-blur-md px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold">Agent Wallets</h1>
              <p className="text-xs text-neutral-400">Manage your agents&apos; wallets and trade on Polymarket</p>
            </div>
          </div>
        </header>

        <div className="p-6">
          {/* Agent list */}
          {agents.length === 0 ? (
            <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-12 text-center">
              <Wallet size={32} className="mx-auto mb-4 text-neutral-500" />
              <h2 className="text-lg font-medium">No agents yet</h2>
              <p className="mt-1 text-sm text-neutral-400">
                Register an agent via the API and claim it here
              </p>
              <code className="mt-4 block rounded-lg bg-neutral-800 p-3 text-xs text-neutral-300 text-left">
                {`curl -X POST "${API_URL}/register" \\`}<br/>
                {`  -H "Content-Type: application/json" \\`}<br/>
                {`  -d '{"agentId": "my-agent"}'`}
              </code>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Agent cards */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {agents.map((a) => (
                  <button
                    key={a.agentId}
                    onClick={() => {
                      setSelectedAgent(a);
                      setBalances(null);
                      setPrivateKey(null);
                    }}
                    className={`rounded-xl border p-5 text-left transition-all ${
                      selectedAgent?.agentId === a.agentId
                        ? "border-emerald-500/50 bg-emerald-500/5"
                        : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500 text-sm font-bold text-white">
                        {a.agentId[0]?.toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{a.agentId}</p>
                        <p className="text-[10px] text-neutral-500">
                          {new Date(a.createdAt).toLocaleDateString()}
                        </p>
                      </div>
                      <ChevronRight size={16} className="text-neutral-500" />
                    </div>
                    <div className="mt-3">
                      <code className="text-[10px] text-neutral-400 font-mono">
                        {truncateAddr(a.walletAddress)}
                      </code>
                    </div>
                  </button>
                ))}
              </div>

              {/* Selected agent detail */}
              {selectedAgent && (
                <div className="space-y-4">
                  <h2 className="text-sm font-semibold text-neutral-300">
                    Agent: <span className="text-white">{selectedAgent.agentId}</span>
                  </h2>

                  {/* Wallet addresses */}
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Wallet size={14} className="text-blue-400" />
                        <span className="text-xs text-neutral-400">EOA Wallet</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <code className="text-xs font-mono">{truncateAddr(selectedAgent.walletAddress)}</code>
                        <button
                          onClick={() => copyToClipboard(selectedAgent.walletAddress, "eoa")}
                          className="rounded p-1 text-neutral-500 hover:text-white"
                        >
                          {copied === "eoa" ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                        </button>
                        <a href={`https://polygonscan.com/address/${selectedAgent.walletAddress}`} target="_blank" rel="noopener noreferrer" className="rounded p-1 text-neutral-500 hover:text-white">
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>
                  </div>

                  {/* API Key input for authenticated features */}
                  <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
                    <label className="mb-2 block text-xs font-medium text-neutral-400">
                      Agent API Key <span className="text-neutral-500">(for balance & key export)</span>
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={apiKeyInput}
                        onChange={(e) => setApiKeyInput(e.target.value)}
                        placeholder="epk_..."
                        className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-3 py-2 text-xs font-mono text-white placeholder:text-neutral-500 focus:border-emerald-500 focus:outline-none"
                      />
                      <button
                        onClick={loadBalance}
                        disabled={!apiKeyInput || balanceLoading}
                        className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-2 text-xs font-medium text-black hover:bg-emerald-400 disabled:opacity-50"
                      >
                        {balanceLoading ? <RefreshCw size={12} className="animate-spin" /> : <Coins size={12} />}
                        Load
                      </button>
                    </div>
                  </div>

                  {/* Balances */}
                  {balances && (
                    <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Coins size={16} className="text-yellow-400" />
                          <span className="text-xs font-semibold">Balances</span>
                        </div>
                        <button onClick={loadBalance} className="text-xs text-neutral-400 hover:text-white">
                          <RefreshCw size={12} className={balanceLoading ? "animate-spin" : ""} />
                        </button>
                      </div>
                      <div className="rounded-lg bg-gradient-to-r from-emerald-500/10 to-blue-500/10 p-3 mb-3">
                        <span className="text-[10px] text-neutral-400">Total</span>
                        <p className="text-xl font-bold">${balances.total_usd.toFixed(2)}</p>
                      </div>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <div className="rounded-lg border border-neutral-800 p-3">
                          <span className="text-[10px] text-neutral-400">EOA</span>
                          <p className="text-sm font-semibold">{balances.eoa.usdc_e.toFixed(2)} <span className="text-[10px] text-neutral-400">USDC.e</span></p>
                        </div>
                        <div className="rounded-lg border border-neutral-800 p-3">
                          <span className="text-[10px] text-neutral-400">Safe</span>
                          <p className="text-sm font-semibold">{balances.safe.usdc_e.toFixed(2)} <span className="text-[10px] text-neutral-400">USDC.e</span></p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Export Key */}
                  <div className="rounded-xl border border-red-900/30 bg-neutral-900/50 p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Key size={16} className="text-red-400" />
                      <span className="text-xs font-semibold">Export Private Key</span>
                    </div>
                    <div className="mb-3 flex items-start gap-2 rounded-lg bg-yellow-500/5 border border-yellow-500/20 p-2">
                      <AlertTriangle size={12} className="mt-0.5 shrink-0 text-yellow-400" />
                      <p className="text-[10px] text-yellow-200/80">
                        Anyone with your private key controls your wallet. Never share it.
                      </p>
                    </div>
                    {!privateKey ? (
                      <button
                        onClick={exportKey}
                        disabled={keyExportLoading || !apiKeyInput}
                        className="flex items-center gap-2 rounded-lg border border-red-800 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/20 disabled:opacity-50"
                      >
                        {keyExportLoading ? <RefreshCw size={12} className="animate-spin" /> : <Key size={12} />}
                        {keyExportLoading ? "Exporting..." : "Export Key"}
                      </button>
                    ) : (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-800 p-2">
                          <code className="flex-1 break-all text-[10px] font-mono text-neutral-200">
                            {showPrivateKey ? privateKey : "•".repeat(64)}
                          </code>
                          <button onClick={() => setShowPrivateKey(!showPrivateKey)} className="shrink-0 rounded p-1 text-neutral-400 hover:text-white">
                            {showPrivateKey ? <EyeOff size={12} /> : <Eye size={12} />}
                          </button>
                          <button onClick={() => copyToClipboard(privateKey, "pk")} className="shrink-0 rounded p-1 text-neutral-400 hover:text-white">
                            {copied === "pk" ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                          </button>
                        </div>
                        <button onClick={() => { setPrivateKey(null); setShowPrivateKey(false); }} className="text-[10px] text-neutral-500 hover:text-neutral-300">
                          Clear key from view
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
