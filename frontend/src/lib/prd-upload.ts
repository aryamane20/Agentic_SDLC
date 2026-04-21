import { planrApiFetch } from "@/lib/planr-user"

export const PRD_ACCEPT =
  ".txt,.md,.markdown,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"

async function readErrorBody(res: Response): Promise<string> {
  try {
    const j = (await res.json()) as { detail?: unknown }
    if (typeof j.detail === "string") return j.detail
    if (Array.isArray(j.detail)) return JSON.stringify(j.detail)
    return res.statusText || `HTTP ${res.status}`
  } catch {
    return res.statusText || `HTTP ${res.status}`
  }
}

/** Text-like PRDs in-browser; PDF/DOCX via backend extract. */
export async function extractPrdText(file: File): Promise<string> {
  const name = file.name.toLowerCase()
  const isPlain =
    file.type.startsWith("text/") ||
    name.endsWith(".txt") ||
    name.endsWith(".md") ||
    name.endsWith(".markdown")

  if (isPlain) {
    const text = await new Promise<string>((resolve, reject) => {
      const r = new FileReader()
      r.onload = () => resolve(String(r.result ?? ""))
      r.onerror = () => reject(new Error("Could not read file"))
      r.readAsText(file, "UTF-8")
    })
    return text
  }

  const form = new FormData()
  form.append("file", file)
  const res = await planrApiFetch("/reports/extract-document", {
    method: "POST",
    body: form,
  })
  if (!res.ok) {
    if (res.status === 413) throw new Error("File is too large. Maximum is 5 MB.")
    if (res.status === 400) throw new Error("Unsupported file type. Use .txt, .md, .pdf, or .docx.")
    if (res.status === 422) throw new Error("The document appears to be empty or unreadable.")
    if (res.status === 501) throw new Error("PDF support is unavailable on this server.")
    throw new Error(await readErrorBody(res))
  }
  const j = (await res.json()) as { text: string }
  return j.text ?? ""
}
