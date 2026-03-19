import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.EIGENPOLY_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ agentId: string }> }
) {
  const { agentId } = await params;
  try {
    const cookie = req.headers.get("cookie") || "";

    const res = await fetch(`${BACKEND_URL}/balance/${agentId}`, {
      headers: { cookie },
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
    console.error("Failed to fetch balance:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
