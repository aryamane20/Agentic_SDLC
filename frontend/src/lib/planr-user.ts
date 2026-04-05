const STORAGE_KEY = "planr_user_id"

function randomId(): string {
  return crypto.randomUUID()
}

/** Stable anonymous id per browser — scopes plan history on the backend. */
export function getPlanrUserId(): string {
  try {
    let id = localStorage.getItem(STORAGE_KEY)
    if (!id || !id.trim()) {
      id = randomId()
      localStorage.setItem(STORAGE_KEY, id)
    }
    return id.trim()
  } catch {
    return randomId()
  }
}

export function planrApiFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const headers = new Headers(init?.headers)
  headers.set("X-Planr-User", getPlanrUserId())
  return fetch(input, { ...init, headers })
}
