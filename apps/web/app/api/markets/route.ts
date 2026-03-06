import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.EIGENPOLY_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const source = searchParams.get("source") || "All";
    
    // We will build a combined list of standard market signals
    let results: any[] = [];
    
    // 1. If Sozu or All, fetch from Sozu Analytics (Free)
    if (source === "All" || source === "Sozu") {
      try {
        const res = await fetch(`${BACKEND_URL}/analytics/opportunities?status=active&minScore=60&limit=15`, {
          cache: "no-store",
        });
        if (res.ok) {
          const sozuData = await res.json();
          const mapped = (Array.isArray(sozuData) ? sozuData : []).map(item => ({
             market: item.market?.question || item.marketSlug || "Unknown Market",
             signal: "OPPORTUNITY",
             confidence: item.opportunityScore || 60,
             source: "Sozu",
             category: item.strategyType || "General",
             date: new Date(item.createdAt || Date.now()).toISOString().split('T')[0]
          }));
          results = [...results, ...mapped];
        }
      } catch (e) {
        console.error("Sozu fetch failed", e);
      }
    }
    
    // 2. If EigenPoly or All, fetch from Trending Markets (Free)
    if (source === "All" || source === "EigenPoly") {
      try {
        const res = await fetch(`${BACKEND_URL}/markets/trending?limit=15`, {
          cache: "no-store",
        });
        if (res.ok) {
          const trendingData = await res.json();
          const mapped = (Array.isArray(trendingData) ? trendingData : []).map(item => ({
             market: item.question || item.slug || "Unknown Market",
             signal: "TRENDING",
             confidence: 50 + Math.floor(Math.random() * 30), // mock confidence for trending
             source: "EigenPoly",
             category: "Trending",
             date: new Date().toISOString().split('T')[0]
          }));
          results = [...results, ...mapped];
        }
      } catch (e) {
        console.error("Trending fetch failed", e);
      }
    }
    
    // Sort by confidence descending
    results.sort((a, b) => b.confidence - a.confidence);
    
    return NextResponse.json(results);
  } catch (err) {
    console.error("Failed to fetch markets:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
