import axios from "axios"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

export interface AIModel {
  provider: string
  model_id: string
  model_name: string
  input_price_per_1m: number
  output_price_per_1m: number
  supports_vision: boolean
  supports_text: boolean
  context_window: number
  is_default: boolean
  is_active?: boolean
}

export interface ScrutinyThreadItem {
  thread_id: string
  thread_name: string
  pdf_filename: string
  authority: string
  overall_verdict: string
  completeness_score_pct?: number | null
  processing_time_seconds?: number | null
  created_at: string
  metadata?: Record<string, unknown>
  raw_verdict?: Record<string, unknown>
}

export interface ReviewRecord {
  review_id: number
  case_id: string
  created_at: string
  reviewer_name: string
  decision: "APPROVED" | "CORRECTION_REQUIRED" | "PENDING" | "NOT_APPLICABLE"
  note: string
}

export interface ScrutinyVerdict {
  overall?: string
  message?: string
  case_id?: string
  thread_id?: string
  pdf_filename?: string
  processing_seconds?: number
  processing_time_seconds?: number
  doc_type?: {
    document_type?: string
    confidence?: number
    [key: string]: unknown
  }
  checklist?: unknown[] | Record<string, unknown>
  compliance_matrix?: unknown[] | Record<string, unknown>
  bylaw_checks?: Record<string, unknown>
  bylaws?: Record<string, unknown>
  structural_analysis?: {
    concrete_grade_psi?: number | string | { value?: number; verified?: boolean }
    slab_thickness_in?: number | string | { value?: number }
    stability_cert_found?: boolean
    parameters?: Record<string, { value?: number | string; verified?: boolean }>
    [key: string]: unknown
  }
  completeness_audit?: {
    completeness_score_pct?: number
    [key: string]: unknown
  }
  violations?: unknown[]
  action_items?: unknown[]
  telemetry?: Record<string, unknown>
  [key: string]: unknown
}

export interface ScrutinyNodeEvent {
  event: "pipeline_start" | "node_start" | "node_complete" | "pipeline_complete" | "error"
  node?: string
  label?: string
  summary?: string
  elapsed_seconds?: number
  details?: Record<string, unknown>
  thread_id?: string
  thread_name?: string
  filename?: string
  authority?: string
  model?: string
  verdict?: ScrutinyVerdict
  case_id?: string
  error?: string
  message?: string
  timestamp?: number
}

export const scrutinyApi = {
  // Health & Service
  getHealth: async () => {
    const res = await apiClient.get("/health")
    return res.data
  },

  // Threads
  getThreads: async (limit = 50): Promise<ScrutinyThreadItem[]> => {
    const res = await apiClient.get(`/api/v1/threads?limit=${limit}`)
    return res.data.threads || []
  },

  getThread: async (threadId: string): Promise<ScrutinyThreadItem> => {
    const res = await apiClient.get(`/api/v1/threads/${threadId}`)
    return res.data
  },

  deleteThread: async (threadId: string) => {
    const res = await apiClient.delete(`/api/v1/threads/${threadId}`)
    return res.data
  },

  // Chat messages - Streaming (with HITL AbortSignal cancellation support)
  streamChatMessage: async (
    threadId: string,
    message: string,
    modelName?: string,
    onChunk?: (delta: string) => void,
    onDone?: (fullReply: string, model: string) => void,
    onError?: (err: string) => void,
    signal?: AbortSignal
  ): Promise<string> => {
    const url = `${API_BASE_URL}/api/v1/threads/${threadId}/chat`
    let accumulated = ""
    let model = modelName || ""

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          model_name: modelName,
        }),
        signal,
      })

      if (!response.ok) {
        throw new Error(`Chat request failed with status: ${response.status}`)
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported in this browser.")
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split("\n")

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                if (onError) onError(data.error)
                throw new Error(data.error)
              }
              if (data.delta) {
                accumulated += data.delta
                if (onChunk) onChunk(data.delta)
              }
              if (data.done) {
                if (data.model) model = data.model
              }
            } catch {
              // Ignore non-json or partial lines
            }
          }
        }
      }

      if (onDone) onDone(accumulated, model)
      return accumulated
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        // HITL User cancelled generation
        const stoppedText = accumulated ? `${accumulated}\n\n*(Generation stopped by user)*` : "*(Generation stopped by user)*"
        if (onDone) onDone(stoppedText, model)
        return stoppedText
      }
      const msg = err instanceof Error ? err.message : "Chat stream error"
      if (onError) onError(msg)
      throw err
    }
  },

  // Chat messages - Fallback / Non-stream legacy
  sendChatMessage: async (
    threadId: string,
    message: string,
    modelName?: string
  ): Promise<{ reply: string; model: string; thread_id: string }> => {
    const res = await apiClient.post(`/api/v1/threads/${threadId}/chat`, {
      message,
      model_name: modelName,
    })
    return res.data
  },

  getChatMessages: async (
    threadId: string,
    limit = 200
  ): Promise<
    Array<{
      message_id: number
      thread_id: string
      sender: string
      content: string
      metadata: Record<string, unknown>
      created_at: string
    }>
  > => {
    const res = await apiClient.get(
      `/api/v1/threads/${threadId}/messages?limit=${limit}`
    )
    return res.data.messages || []
  },

  // Scrutinize
  scrutinizeFile: async (
    file: File,
    authority = "DHA_Lahore",
    plotId?: string,
    revision?: string,
    modelName?: string,
    threadId?: string,
    onUploadProgress?: (progressEvent: unknown) => void
  ) => {
    const formData = new FormData()
    formData.append("file", file)
    if (authority) formData.append("authority", authority)
    if (plotId) formData.append("plot_id", plotId)
    if (revision) formData.append("revision", revision)
    if (modelName) formData.append("model_name", modelName)
    if (threadId) formData.append("thread_id", threadId)

    const res = await apiClient.post("/api/v1/scrutinize", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    })
    return res.data
  },

  // Scrutinize with real-time LangGraph node streaming (SSE, with HITL cancellation support)
  streamScrutinizeFile: async (
    file: File,
    authority = "DHA_Lahore",
    plotId?: string,
    revision?: string,
    modelName?: string,
    threadId?: string,
    onEvent?: (event: ScrutinyNodeEvent) => void,
    onComplete?: (result: { verdict: ScrutinyVerdict; case_id?: string; thread_id?: string; elapsed_seconds?: number }) => void,
    onError?: (err: string) => void,
    signal?: AbortSignal
  ) => {
    const formData = new FormData()
    formData.append("file", file)
    if (authority) formData.append("authority", authority)
    if (plotId) formData.append("plot_id", plotId)
    if (revision) formData.append("revision", revision)
    if (modelName) formData.append("model_name", modelName)
    if (threadId) formData.append("thread_id", threadId)

    const url = `${API_BASE_URL}/api/v1/scrutinize/stream`
    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData,
        signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        let detail = "Streaming scrutiny request failed"
        try {
          const parsed = JSON.parse(errorText)
          detail = parsed.detail?.message || parsed.detail || detail
        } catch {
          detail = errorText || detail
        }
        onError?.(detail)
        return
      }

      if (!response.body) {
        onError?.("No response body received from stream")
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith("data:")) continue

          try {
            const dataStr = trimmed.replace(/^data:\s*/, "")
            const event: ScrutinyNodeEvent = JSON.parse(dataStr)

            onEvent?.(event)

            if (event.event === "pipeline_complete" && event.verdict) {
              onComplete?.({
                verdict: event.verdict,
                case_id: event.case_id,
                thread_id: event.thread_id,
                elapsed_seconds: event.elapsed_seconds,
              })
            } else if (event.event === "error") {
              onError?.(event.message || event.error || "Scrutiny stream failed")
            }
          } catch {
            // Incomplete JSON or malformed chunk
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        // HITL User aborted scrutiny pipeline
        onError?.("Scrutiny pipeline stopped by user.")
        return
      }
      const msg = err instanceof Error ? err.message : "Network error during scrutiny stream"
      onError?.(msg)
    }
  },

  // Download PDF Report
  downloadPdfReport: async (verdict: ScrutinyVerdict) => {
    const res = await apiClient.post("/api/v1/reports/pdf", verdict, {
      responseType: "blob",
    })
    return res.data
  },

  // Models
  getModels: async (): Promise<{ models: AIModel[]; active_system_model: string }> => {
    const res = await apiClient.get("/api/v1/models")
    return res.data
  },

  getProviders: async (): Promise<string[]> => {
    const res = await apiClient.get("/api/v1/models/providers")
    return res.data.providers || []
  },

  selectModel: async (modelId: string) => {
    const res = await apiClient.post(`/api/v1/models/${encodeURIComponent(modelId)}/select`)
    return res.data
  },

  addModel: async (model: Omit<AIModel, "is_active">) => {
    const res = await apiClient.post("/api/v1/models", model)
    return res.data
  },

  deleteModel: async (modelId: string) => {
    const res = await apiClient.delete(`/api/v1/models/${encodeURIComponent(modelId)}`)
    return res.data
  },

  // Bylaws
  getBylaws: async () => {
    const res = await apiClient.get("/api/v1/bylaws")
    return res.data
  },

  // Reviews
  getCase: async (caseId: string) => {
    const res = await apiClient.get(`/api/v1/cases/${caseId}`)
    return res.data
  },

  addReview: async (caseId: string, reviewerName: string, decision: string, note = "") => {
    const res = await apiClient.post(`/api/v1/cases/${caseId}/reviews`, {
      reviewer_name: reviewerName,
      decision,
      note,
    })
    return res.data
  },

  getEvidenceImageUrl: (caseId: string, pageNumber: number) => {
    return `${API_BASE_URL}/api/v1/cases/${caseId}/evidence/${pageNumber}`
  },
}
