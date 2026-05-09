export type ApiResult<T> = {
  ok: boolean;
  data?: T;
  error?: string;
};

export async function safeJsonFetch<T>(url: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(url, {
      headers: {
        accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return { ok: false, error: `HTTP ${response.status}` };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "unknown error",
    };
  }
}
