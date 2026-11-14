import { backend } from "@/lib/proxy";
export async function GET() { return backend("/api/research/domains"); }
