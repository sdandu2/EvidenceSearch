import { NextRequest, NextResponse } from "next/server";
import { backend } from "@/lib/proxy";

export async function POST(request: NextRequest) {
  let payload: unknown;
  try { payload = await request.json(); }
  catch { return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 }); }
  if (!payload || typeof payload !== "object" || !("query" in payload))
    return NextResponse.json({ detail: "Provide a scientific query" }, { status: 400 });
  const query = (payload as { query: unknown }).query;
  if (typeof query !== "string" || query.trim().length < 3 || query.length > 600)
    return NextResponse.json({ detail: "Query length must be 3–600 characters" }, { status: 422 });
  // Construct a fresh fixed schema; don't forward arbitrary client keys.
  return backend("/api/search", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: query.trim(), limit: 10 }),
  });
}
