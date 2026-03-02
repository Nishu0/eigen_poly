import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.EIGENPOLY_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const cookie = req.headers.get("cookie") || "";
    const { searchParams } = new URL(req.url);

    // Forward query params (limit, offset, agent_id)
    const params = new URLSearchParams();
    if (searchParams.get("limit")) params.set("limit", searchParams.get("limit")!);
    if (searchParams.get("offset")) params.set("offset", searchParams.get("offset")!);
    if (searchParams.get("agent_id")) params.set("agent_id", searchParams.get("agent_id")!);

    const qs = params.toString() ? `?${params}` : "";

    const res = await fetch(`${BACKEND_URL}/user/logs${qs}`, {
      headers: { cookie },
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { logs: [], total: 0, error: `Backend returned ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Failed to fetch logs:", err);
    return NextResponse.json({ logs: [], total: 0 });
  }
}
