import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.EIGENPOLY_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const cookie = req.headers.get("cookie") || "";
    const body = await req.json();

    const res = await fetch(`${BACKEND_URL}/export-solana-key`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        cookie,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail || data.error || `Backend returned ${res.status}` },
        { status: res.status }
      );
    }

    return NextResponse.json(data);
  } catch (err) {
    console.error("Failed to export Solana key:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
