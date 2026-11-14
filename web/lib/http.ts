export async function apiJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = typeof payload?.detail === "string" ? payload.detail : message;
    } catch { /* avoid masking HTTP error */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
