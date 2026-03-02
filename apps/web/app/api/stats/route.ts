import { NextResponse } from "next/server";

const BACKEND_URL = process.env.EIGENPOLY_API_URL || "https://api.eigenpoly.xyz";

export const revalidate = 60; // revalidate every 60 seconds

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/stats`, {
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      throw new Error(`Backend returned ${res.status}`);
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("Failed to fetch stats:", err);
    // Return fallback data so landing page never breaks
    return NextResponse.json({
      agents: 0,
      trades: 0,
      volume_usd: 0,
      open_positions: 0,
    });
  }
}
