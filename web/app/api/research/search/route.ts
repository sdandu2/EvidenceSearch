import { NextRequest, NextResponse } from "next/server";
const fields = new Set(["Neuroscience", "Climate Science", "Quantum Computing", "Genetics", "Immunology"]);
export async function POST(request: NextRequest) {
  let payload: Record<string, unknown>;
  try { payload = await request.json(); }
  catch { return NextResponse.json({ detail: "Invalid JSON" }, {status:400}); }
  const query = typeof payload?.query === "string" ? payload.query.trim() : "";
  const domain = typeof payload?.domain === "string" ? payload.domain : "";
  if (query.length < 3 || query.length > 600 || !fields.has(domain))
    return NextResponse.json({detail:"Enter a question and select a supported field"},{status:422});
  const yearMin = payload?.year_min == null ? null : Number(payload.year_min);
  const yearMax = payload?.year_max == null ? null : Number(payload.year_max);
  if ([yearMin,yearMax].some(x => x !== null && (!Number.isInteger(x) || x < 1800 || x > 2100)))
    return NextResponse.json({detail:"Invalid publication year"},{status:422});
  try {
    // Initial local model initialization can be slower than subsequent warm searches.
    const api = process.env.API_BASE_URL || "http://127.0.0.1:8000";
    const response = await fetch(`${api}/api/research/search`, {
      method:"POST", cache:"no-store", signal:AbortSignal.timeout(180000),
      headers:{"content-type":"application/json"},
      body:JSON.stringify({query,domain,limit:10,year_min:yearMin,year_max:yearMax})
    });
    return new NextResponse(await response.text(),{status:response.status,
      headers:{"content-type":"application/json","cache-control":"no-store"}});
  } catch {
    return NextResponse.json({detail:"Local expanded search is unavailable. Check the FastAPI terminal."},{status:503});
  }
}
