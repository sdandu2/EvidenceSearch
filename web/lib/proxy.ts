import { NextResponse } from "next/server";

const origin = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function backend(path: string, init?: RequestInit) {
  try {
    const response = await fetch(`${origin}${path}`, {
      ...init,
      cache: "no-store",
      signal: AbortSignal.timeout(60000),
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") || "application/json", "cache-control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "The retrieval service is unavailable. Start the FastAPI backend and retry." }, { status: 503 });
  }
}
