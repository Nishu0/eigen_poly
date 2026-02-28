"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Shield,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  Wallet,
  ArrowRight,
  Eye,
  DollarSign,
  PenTool,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DeviceInfo {
  status: string;
  agentId: string;
  walletAddress?: string;
  scopes?: string[];
  permissions?: string[];
  message?: string;
}

interface UserInfo {
  userId: string;
  email: string;
  name: string;
  avatarUrl: string;
}

export default function DevicePage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white">
          <RefreshCw size={24} className="animate-spin text-neutral-400" />
        </main>
      }
    >
      <DeviceContent />
    </Suspense>
  );
}

function DeviceContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") || "";

  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [result, setResult] = useState<{ status: string; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check if user is logged in
  useEffect(() => {
    fetch(`${API_URL}/oauth/me`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUser(data))
      .catch(() => setUser(null));
  }, []);

  // Fetch device info
  useEffect(() => {
    if (!code) {
      setError("No claim code provided");
      setLoading(false);
      return;
    }
    fetch(`${API_URL}/device/${code}`)
      .then((r) => {
        if (!r.ok) throw new Error("Invalid or expired claim code");
        return r.json();
      })
      .then((data) => {
        setDeviceInfo(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, [code]);

  const handleAuthorize = async () => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_URL}/device/authorize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Authorization failed");
      setResult({ status: "authorized", message: data.message });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeny = async () => {
    setActionLoading(true);
    try {
      await fetch(`${API_URL}/device/deny`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ code }),
      });
      setResult({ status: "denied", message: "Agent claim denied." });
    } catch {} finally {
      setActionLoading(false);
    }
  };

  const loginUrl = `${API_URL}/oauth/google?redirect=/device?code=${code}`;

  // ────── Loading ──────
  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white">
        <RefreshCw size={24} className="animate-spin text-neutral-400" />
      </main>
    );
  }

  // ────── Error ──────
  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
        <div className="w-full max-w-md rounded-2xl border border-red-900/30 bg-neutral-900/50 p-8 text-center">
          <AlertTriangle size={32} className="mx-auto mb-4 text-red-400" />
          <h1 className="text-lg font-semibold">Error</h1>
          <p className="mt-2 text-sm text-neutral-400">{error}</p>
        </div>
      </main>
    );
  }

  // ────── Already handled ──────
  if (result) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
        <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
          {result.status === "authorized" ? (
            <>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
                <Check size={28} className="text-emerald-400" />
              </div>
              <h1 className="text-lg font-semibold">Agent Authorized!</h1>
              <p className="mt-2 text-sm text-neutral-400">{result.message}</p>
              <a
                href="/dashboard"
                className="mt-6 inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-6 py-2.5 text-sm font-medium text-black transition-all hover:bg-emerald-400"
              >
                Go to Dashboard <ArrowRight size={16} />
              </a>
            </>
          ) : (
            <>
              <X size={28} className="mx-auto mb-4 text-red-400" />
              <h1 className="text-lg font-semibold">Claim Denied</h1>
              <p className="mt-2 text-sm text-neutral-400">{result.message}</p>
            </>
          )}
        </div>
      </main>
    );
  }

  // ────── Device info loaded but not pending ──────
  if (deviceInfo && deviceInfo.status !== "pending") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
        <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8 text-center">
          <Shield size={28} className="mx-auto mb-4 text-neutral-400" />
          <h1 className="text-lg font-semibold">Code Already Used</h1>
          <p className="mt-2 text-sm text-neutral-400">{deviceInfo.message}</p>
        </div>
      </main>
    );
  }

  // ────── Not logged in — show login ──────
  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
        <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8">
          <div className="mb-6 text-center">
            {/* Icons */}
            <div className="mb-4 flex items-center justify-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-800 border border-neutral-700">
                <span className="text-lg font-mono">{">_"}</span>
              </div>
              <ArrowRight size={20} className="text-neutral-500" />
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <Shield size={20} className="text-emerald-400" />
              </div>
            </div>
            <h1 className="text-xl font-semibold">Connect Agent to EigenPoly</h1>
            <p className="mt-1 text-sm text-neutral-400">
              Code: <code className="rounded bg-neutral-800 px-2 py-0.5 text-emerald-400">{code}</code>
            </p>
          </div>

          <div className="space-y-3">
            <a
              href={loginUrl}
              className="flex w-full items-center justify-center gap-3 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-neutral-700"
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

          <p className="mt-4 text-center text-xs text-neutral-500">
            Sign in to authorize this agent
          </p>
        </div>
      </main>
    );
  }

  // ────── Logged in — show permissions ──────
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0A0A0A] text-white px-4">
      <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900/50 p-8">
        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mb-4 flex items-center justify-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-neutral-800 border border-neutral-700">
              <span className="text-lg font-mono">{">_"}</span>
            </div>
            <ArrowRight size={20} className="text-neutral-500" />
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <Shield size={20} className="text-emerald-400" />
            </div>
          </div>
          <h1 className="text-xl font-semibold">Connect Agent to EigenPoly</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Code: <code className="rounded bg-neutral-800 px-2 py-0.5 text-emerald-400">{code}</code>
          </p>
        </div>

        {/* Permissions */}
        <div className="mb-6">
          <p className="mb-3 text-xs font-medium text-neutral-400 uppercase tracking-wider">
            This agent will be able to:
          </p>
          <div className="space-y-2">
            {[
              { icon: Eye, label: "View wallet balances" },
              { icon: DollarSign, label: "Place trades on Polymarket" },
              { icon: PenTool, label: "Sign on-chain transactions" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-3 rounded-lg bg-neutral-800/50 px-3 py-2.5">
                <Check size={16} className="text-emerald-400 shrink-0" />
                <span className="text-sm">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Agent info */}
        <div className="mb-6 rounded-lg border border-neutral-700 bg-neutral-800/30 p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-neutral-400">Agent</span>
            <span className="font-medium">{deviceInfo?.agentId}</span>
          </div>
          {deviceInfo?.walletAddress && (
            <div className="mt-2 flex items-center justify-between text-xs">
              <span className="text-neutral-400">Wallet</span>
              <code className="text-neutral-300 font-mono text-[10px]">
                {deviceInfo.walletAddress.slice(0, 6)}...{deviceInfo.walletAddress.slice(-4)}
              </code>
            </div>
          )}
        </div>

        {/* Claiming notice */}
        <div className="mb-6 flex items-start gap-2 rounded-lg bg-blue-500/5 border border-blue-500/20 p-3">
          <Shield size={14} className="mt-0.5 shrink-0 text-blue-400" />
          <div className="text-xs text-blue-200/80">
            <p className="font-medium">Secure connection</p>
            <p className="mt-0.5">Your API key will be shown once in your terminal. You can revoke access from your dashboard at any time.</p>
          </div>
        </div>

        {/* Logged in as */}
        <div className="mb-4 flex items-center gap-2 text-xs text-neutral-400">
          <span>Logged in as</span>
          <span className="font-medium text-white">{user.email}</span>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleDeny}
            disabled={actionLoading}
            className="flex-1 rounded-lg border border-neutral-700 px-4 py-2.5 text-sm font-medium text-neutral-300 transition-colors hover:bg-neutral-800 disabled:opacity-50"
          >
            Deny
          </button>
          <button
            onClick={handleAuthorize}
            disabled={actionLoading}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-black transition-all hover:bg-emerald-400 disabled:opacity-50"
          >
            {actionLoading ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : null}
            Authorize
          </button>
        </div>
      </div>
    </main>
  );
}
