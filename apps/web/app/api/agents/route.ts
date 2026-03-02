import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.EIGENPOLY_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    // Forward session cookie so backend can identify the logged-in user
    const cookie = req.headers.get("cookie") || "";

    const res = await fetch(`${BACKEND_URL}/user/agents`, {
      headers: { cookie },
      cache: "no-store",
    });

    if (!res.ok) {
      return NextResponse.json(
        { agents: [], error: `Backend returned ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Failed to fetch user agents:", err);
    return NextResponse.json({ agents: [] });
  }
}
