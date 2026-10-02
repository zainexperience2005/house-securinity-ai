"use client"

import * as React from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { NativeSelect } from "@/components/ui/native-select"
import { Badge } from "@/components/ui/badge"
import { ReportViewer } from "@/components/report-viewer"
import { SettingsDialog } from "@/components/settings-dialog"
import { MarkdownRenderer } from "@/components/markdown-renderer"
import { scrutinyApi, type ScrutinyVerdict } from "@/lib/api"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Upload,
  FileText,
  Building,
  Sparkles,
  ArrowUp,
  Cpu,
  RefreshCw,
  CheckCircle2,
  Clock,
  Activity,
  Eye,
  Copy,
  Check,
  Download,
  ExternalLink,
  Square,
} from "lucide-react"

export interface PipelineStage {
  node: string
  label: string
  defaultDesc: string
  status: "pending" | "running" | "completed"
  summary?: string
  elapsedSeconds?: number
}

const INITIAL_STAGES: PipelineStage[] = [
  {
    node: "ingest",
    label: "Stage 1: Document Ingestion & CAD Vector Geometry Extraction",
    defaultDesc: "Parsing PDF sheets, extracting CAD vector paths, and verifying document integrity...",
    status: "pending",
  },
  {
    node: "gate",
    label: "Stage 2: Title Block Detection & Sheet Classification Gate",
    defaultDesc: "Analyzing title blocks, sheet classification, and municipal audit eligibility...",
    status: "pending",
  },
  {
    node: "crop",
    label: "Stage 3: Region-of-Interest (ROI) Intelligent Cropping",
    defaultDesc: "Generating high-resolution crops targeting schedules, structural notes, and plans...",
    status: "pending",
  },
  {
    node: "extract",
    label: "Stage 4: Multimodal Vision & Parameter Extraction",
    defaultDesc: "Extracting concrete grade, slab thickness, steel rebar specs, and setback measurements...",
    status: "pending",
  },
  {
    node: "judge",
    label: "Stage 5: Municipal Bylaw Compliance Verification",
    defaultDesc: "Auditing extracted measurements against statutory housing authority rules...",
    status: "pending",
  },
  {
    node: "report",
    label: "Stage 6: Final Compliance Verdict & Immutable Case Persistence",
    defaultDesc: "Synthesizing comprehensive audit matrix, saving case record, and finalizing verdict...",
    status: "pending",
  },
]

interface Message {
  id: string
  sender: "user" | "assistant"
  text?: string
  file?: {
    name: string
    size: number
  }
  verdict?: ScrutinyVerdict
  caseId?: string | null
  timestamp: string
}

interface ChatInterfaceProps {
  currentThreadId: string | null
  activeModel: string
  onThreadCreated: (threadId: string) => void
  onModelChanged?: (modelId: string) => void
}

const AUTHORITIES = [
  { value: "DHA_Lahore", label: "DHA Lahore (Defence Housing Authority)" },
  { value: "LDA_Lahore", label: "LDA Lahore (Lahore Development Authority)" },
  { value: "CDA_Islamabad", label: "CDA Islamabad (Capital Development Authority)" },
  { value: "Bahria_Town", label: "Bahria Town (Housing & Infrastructure)" },
  { value: "OPF_Islamabad", label: "OPF Housing Scheme Islamabad" },
]

export function ChatInterface({
  currentThreadId,
  activeModel,
  onThreadCreated,
  onModelChanged,
}: ChatInterfaceProps) {
  const [messages, setMessages] = React.useState<Message[]>([])
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null)
  const [selectedAuthority, setSelectedAuthority] = React.useState("DHA_Lahore")
  const [plotId, setPlotId] = React.useState("")
  const [revision, setRevision] = React.useState("Rev 0")
  const [inputText, setInputText] = React.useState("")
  const [isScrutinizing, setIsScrutinizing] = React.useState(false)
  const [isChatLoading, setIsChatLoading] = React.useState(false)
  const [isLoadingThread, setIsLoadingThread] = React.useState<boolean>(Boolean(currentThreadId))
  const [pipelineStages, setPipelineStages] = React.useState<PipelineStage[]>(INITIAL_STAGES)
  const [streamElapsed, setStreamElapsed] = React.useState(0)
  const [liveParams, setLiveParams] = React.useState<Record<string, unknown>>({})

  // Final PDF Reader Modal State
  const [pdfDialogOpen, setPdfDialogOpen] = React.useState(false)
  const [pdfUrl, setPdfUrl] = React.useState<string | null>(null)
  const [loadingPdf, setLoadingPdf] = React.useState(false)

  // Message Copy State
  const [copiedMsgId, setCopiedMsgId] = React.useState<string | null>(null)

  const handleCopyMessage = (id: string, text?: string) => {
    if (!text) return
    navigator.clipboard.writeText(text)
    setCopiedMsgId(id)
    toast.success("Message Copied", {
      description: "Content copied to clipboard.",
    })
    setTimeout(() => setCopiedMsgId(null), 2000)
  }

  // HITL AbortControllers for user cancellation
  const chatAbortControllerRef = React.useRef<AbortController | null>(null)
  const scrutinyAbortControllerRef = React.useRef<AbortController | null>(null)

  const handleStopChatGeneration = () => {
    if (chatAbortControllerRef.current) {
      chatAbortControllerRef.current.abort()
      chatAbortControllerRef.current = null
      setIsChatLoading(false)
      toast.info("Generation Stopped", {
        description: "AI response generation was stopped by user (HITL).",
      })
    }
  }

  const handleStopScrutiny = () => {
    if (scrutinyAbortControllerRef.current) {
      scrutinyAbortControllerRef.current.abort()
      scrutinyAbortControllerRef.current = null
      setIsScrutinizing(false)
      toast.info("Scrutiny Stopped", {
        description: "Scrutiny pipeline execution was stopped by user (HITL).",
      })
    }
  }

  // Find latest scrutiny verdict from messages
  const latestReportMessage = React.useMemo(() => {
    return messages.slice().reverse().find((m) => Boolean(m.verdict))
  }, [messages])

  const latestVerdict = latestReportMessage?.verdict

  // Invalidate cached PDF url when switching threads or new verdict arrives
  React.useEffect(() => {
    setPdfUrl(null)
  }, [latestVerdict?.case_id, latestVerdict?.thread_id, currentThreadId])

  const handleOpenPdfDialog = async () => {
    setPdfDialogOpen(true)
    if (!latestVerdict) return
    if (pdfUrl) return

    setLoadingPdf(true)
    try {
      const blob = await scrutinyApi.downloadPdfReport(latestVerdict)
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }))
      setPdfUrl(url)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error generating PDF report"
      toast.error("Could not load PDF", { description: msg })
    } finally {
      setLoadingPdf(false)
    }
  }

  const fileInputRef = React.useRef<HTMLInputElement | null>(null)
  const messagesEndRef = React.useRef<HTMLDivElement | null>(null)

  // Live timer tick during scrutiny
  React.useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isScrutinizing) {
      interval = setInterval(() => {
        setStreamElapsed((prev) => prev + 1)
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isScrutinizing])

  // Scroll to bottom on new messages
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isScrutinizing, pipelineStages])

  // Load thread history when currentThreadId changes
  React.useEffect(() => {
    if (!currentThreadId) {
      setMessages([])
      setIsLoadingThread(false)
      return
    }

    setIsLoadingThread(true)
    let isCancelled = false

    scrutinyApi
      .getThread(currentThreadId)
      .then(async (record) => {
        if (isCancelled) return
        if (record && record.raw_verdict) {
          const baseMessages: Message[] = [
            {
              id: `user-${record.thread_id}`,
              sender: "user",
              text: `Scrutinize drawing submission according to ${record.authority || "DHA"} bylaws.`,
              file: {
                name: record.pdf_filename || record.thread_name,
                size: 1024 * 1024 * 2.4,
              },
              timestamp: record.created_at,
            },
            {
              id: `assistant-${record.thread_id}`,
              sender: "assistant",
              verdict: record.raw_verdict as ScrutinyVerdict,
              caseId: (record.raw_verdict as ScrutinyVerdict).case_id || `CASE-${record.thread_id.slice(-8).toUpperCase()}`,
              timestamp: record.created_at,
            },
          ]

          // Load persisted follow-up chat messages from the database
          try {
            const chatHistory = await scrutinyApi.getChatMessages(currentThreadId)
            if (!isCancelled) {
              const chatMessages: Message[] = chatHistory.map((m) => ({
                id: `chat-${m.message_id}`,
                sender: m.sender as "user" | "assistant",
                text: m.content,
                timestamp: m.created_at,
              }))
              setMessages([...baseMessages, ...chatMessages])
            }
          } catch {
            if (!isCancelled) setMessages(baseMessages)
          }
        }
      })
      .catch(() => {
        if (!isCancelled) {
          toast.error("Failed to load thread history")
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoadingThread(false)
        }
      })

    return () => {
      isCancelled = true
    }
  }, [currentThreadId])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        toast.error("Invalid File Type", {
          description: "Only PDF drawing packages are supported.",
        })
        return
      }
      setSelectedFile(file)
      toast.success("Drawing Package Attached", {
        description: `${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
      })
    }
  }

  const handleRunScrutiny = async () => {
    if (!selectedFile) {
      toast.error("No File Selected", {
        description: "Please attach an architectural or structural drawing PDF first.",
      })
      return
    }

    const file = selectedFile
    const nowIso = new Date().toISOString()
    const userMsgId = `user-${Date.now()}`

    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: "user",
        text: `Execute autonomous compliance scrutiny on ${file.name} for ${selectedAuthority} (Plot ID: ${plotId || "N/A"}).`,
        file: {
          name: file.name,
          size: file.size,
        },
        timestamp: nowIso,
      },
    ])

    setSelectedFile(null)
    setIsScrutinizing(true)
    setStreamElapsed(0)
    setLiveParams({})

    // Reset stages: stage 0 is running, rest are pending
    const initialRunStages: PipelineStage[] = INITIAL_STAGES.map((s, idx) => ({
      ...s,
      status: idx === 0 ? "running" : "pending",
      summary: undefined,
      elapsedSeconds: undefined,
    }))
    setPipelineStages(initialRunStages)

    const abortController = new AbortController()
    scrutinyAbortControllerRef.current = abortController

    try {
      await scrutinyApi.streamScrutinizeFile(
        file,
        selectedAuthority,
        plotId || undefined,
        revision || undefined,
        activeModel,
        currentThreadId || undefined,
        (event) => {
          if (event.event === "node_complete" && event.node) {
            setPipelineStages((prev) => {
              const nodeIdx = prev.findIndex((s) => s.node === event.node)
              return prev.map((s, idx) => {
                if (s.node === event.node) {
                  return {
                    ...s,
                    status: "completed",
                    summary: event.summary,
                    elapsedSeconds: event.elapsed_seconds,
                  }
                } else if (idx === nodeIdx + 1) {
                  return {
                    ...s,
                    status: "running",
                  }
                }
                return s
              })
            })

            // Capture live parameter discoveries
            if (event.details?.parameters && typeof event.details.parameters === "object") {
              setLiveParams((prev) => ({
                ...prev,
                ...(event.details?.parameters as Record<string, unknown>),
              }))
            }
            if (event.details?.document_type) {
              setLiveParams((prev) => ({
                ...prev,
                "Document Type": String(event.details?.document_type).replace(/_/g, " "),
              }))
            }
          }
        },
        (result) => {
          setIsScrutinizing(false)
          scrutinyAbortControllerRef.current = null
          // Mark all stages as completed
          setPipelineStages((prev) =>
            prev.map((s) => ({ ...s, status: "completed" }))
          )

          const verdict = result.verdict
          const caseId = result.case_id || (verdict ? verdict.case_id : null)
          const threadId = result.thread_id || (verdict ? verdict.thread_id : undefined)

          if (threadId) {
            onThreadCreated(threadId)
          }

          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              sender: "assistant",
              verdict: verdict,
              caseId: caseId,
              timestamp: new Date().toISOString(),
            },
          ])

          toast.success("Autonomous Scrutiny Completed", {
            description: `Verdict: ${verdict?.overall || "Generated"} in ${result.elapsed_seconds || 5}s`,
          })
        },
        (errMsg) => {
          setIsScrutinizing(false)
          scrutinyAbortControllerRef.current = null
          toast.error("Scrutiny Failed", {
            description: errMsg,
          })
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-err-${Date.now()}`,
              sender: "assistant",
              text: `⚠️ Audit Execution Interrupted: ${errMsg}`,
              timestamp: new Date().toISOString(),
            },
          ])
        },
        abortController.signal
      )
    } catch (err: unknown) {
      setIsScrutinizing(false)
      scrutinyAbortControllerRef.current = null
      const errMsg = err instanceof Error ? err.message : "Scrutiny stream invocation error"
      toast.error("Scrutiny Failed", { description: errMsg })
    }
  }

  // Handle follow-up chat text query
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) return

    // A thread must exist before chatting (the PDF scrutiny must have run first)
    if (!currentThreadId) {
      toast.error("No Active Thread", {
        description: "Please run a PDF scrutiny first to create a thread before chatting.",
      })
      return
    }

    const q = inputText.trim()
    const nowIso = new Date().toISOString()

    // Optimistically add the user message to the UI
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        sender: "user",
        text: q,
        timestamp: nowIso,
      },
    ])
    setInputText("")
    setIsChatLoading(true)

    const assistantMsgId = `assistant-reply-${Date.now()}`

    // Optimistically insert an empty assistant message placeholder for the stream
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        sender: "assistant",
        text: "",
        timestamp: new Date().toISOString(),
      },
    ])

    const abortController = new AbortController()
    chatAbortControllerRef.current = abortController

    try {
      await scrutinyApi.streamChatMessage(
        currentThreadId,
        q,
        activeModel,
        // onChunk: append incoming delta tokens in real-time
        (delta) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? { ...msg, text: msg.text + delta }
                : msg
            )
          )
        },
        // onDone: finalized
        () => { },
        // onError: handle error
        (err) => {
          toast.error("Chat Stream Error", { description: err })
        },
        abortController.signal
      )
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") {
        // User deliberately aborted generation; do not display as error
        return
      }
      let errMsg = "Chat request failed"
      if (err instanceof Error) errMsg = err.message

      toast.error("Chat Error", { description: errMsg })

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, text: `⚠️ ${errMsg}` }
            : msg
        )
      )
    } finally {
      chatAbortControllerRef.current = null
      setIsChatLoading(false)
    }
  }

  return (
    <div className="flex h-screen flex-1 flex-col overflow-hidden bg-background">
      {/* Top Bar */}
      <div className="flex items-center justify-between border-b px-5 py-2.5">
        <div className="flex items-center gap-2">
          <Building className="size-4 text-muted-foreground" />
          <span className="text-xs font-semibold text-foreground">
            Auditing Authority:
          </span>
          <NativeSelect
            size="sm"
            value={selectedAuthority}
            onChange={(e) => setSelectedAuthority(e.target.value)}
            className="text-xs font-medium"
          >
            {AUTHORITIES.map((auth) => (
              <option key={auth.value} value={auth.value}>
                {auth.label}
              </option>
            ))}
          </NativeSelect>
        </div>

        <div className="flex items-center gap-3">
          <SettingsDialog
            activeModel={activeModel}
            onModelSelected={(modelId) => {
              onModelChanged?.(modelId)
            }}
            trigger={
              <button
                type="button"
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 px-2 py-1 rounded-md transition-colors cursor-pointer border border-transparent hover:border-border"
                title="Change active AI model"
              >
                <Cpu className="size-3.5 text-primary" />
                <span className="font-mono text-[11px] font-medium">{activeModel}</span>
              </button>
            }
          />
          <NativeSelect
            size="sm"
            value={revision}
            onChange={(e) => {
              const newRev = e.target.value
              setRevision(newRev)
              toast.info(`Active Revision switched to ${newRev}`, {
                description: "Subsequent drawings and scrutiny runs will be audited as " + newRev + ".",
              })
            }}
            className="text-[11px] font-mono font-medium h-7"
            title="Switch drawing revision"
          >
            <option value="Rev 0">Rev 0</option>
            <option value="Rev 1">Rev 1</option>
            <option value="Rev 2">Rev 2</option>
            <option value="Rev 3">Rev 3</option>
          </NativeSelect>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 space-y-6">
        {isLoadingThread ? (
          /* SKELETON / LOADING STATE FOR THREAD RELOAD */
          <div className="mx-auto max-w-2xl py-16 flex flex-col items-center justify-center space-y-5 animate-in fade-in-50 duration-200">
            <div className="relative flex items-center justify-center">
              <div className="absolute -inset-2 rounded-2xl bg-primary/10 blur-md animate-pulse" />
              <div className="relative flex size-16 items-center justify-center rounded-2xl border border-border/80 bg-transparent p-2.5 shadow-xs">
                <Image
                  src="/ezypro_logo.png"
                  alt="Ezypro Logo"
                  width={70}
                  height={70}
                  className="object-contain"
                  priority
                />
              </div>
              <div className="absolute -inset-1 rounded-2xl border-2 border-transparent border-t-primary border-r-primary/50 animate-spin" />
            </div>
            <div className="text-center space-y-1.5 max-w-md">
              <h3 className="text-sm font-semibold tracking-tight text-foreground">
                Loading Scrutiny Case Findings...
              </h3>
              <p className="text-xs text-muted-foreground font-mono">
                Restoring compliance report, spatial matrix, and drawing evidence.
              </p>
            </div>
            {/* Shimmer skeleton placeholders */}
            <div className="w-full space-y-3 pt-3">
              <div className="h-16 w-full rounded-xl border border-border/50 bg-muted/25 animate-pulse" />
              <div className="h-48 w-full rounded-xl border border-border/50 bg-muted/20 animate-pulse" />
              <div className="h-24 w-full rounded-xl border border-border/50 bg-muted/15 animate-pulse" />
            </div>
          </div>
        ) : messages.length === 0 && !isScrutinizing ? (
          /* EMPTY STATE / WELCOME CARD */
          <div className="mx-auto max-w-2xl py-6 space-y-6">
            <div className="text-center space-y-2">
              <div className="mx-auto flex size-14 items-center justify-center rounded-2xl border border-border/80 bg-white dark:bg-white/95 p-2 shadow-xs">
                <Image
                  src="/ezypro_logo.png"
                  alt="Ezypro Logo"
                  width={42}
                  height={42}
                  className="object-contain"
                />
              </div>
              <h1 className="text-2xl font-bold tracking-tight">
                House Scrutiny AI
              </h1>
              <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                Autonomous architectural and structural CAD drawing verification according to municipal building bylaws (DHA, LDA, CDA, etc.).
              </p>
            </div>

            {/* Upload Box Card */}
            <div className="rounded-xl border bg-card p-6 shadow-xs space-y-4">
              <div
                onClick={() => fileInputRef.current?.click()}
                className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border p-8 text-center cursor-pointer hover:border-foreground/50 transition-colors bg-muted/10"
              >
                <Upload className="size-8 text-muted-foreground mb-2" />
                <p className="text-sm font-semibold text-foreground">
                  {selectedFile ? selectedFile.name : "Click to select Drawing PDF or drag & drop"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Architectural floor plans, structural framing, elevations, and stability certificates.
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>

              {/* Submission Metadata */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Plot ID / Reference (Optional)
                  </label>
                  <Input
                    placeholder="e.g. Plot-93B-OPF"
                    value={plotId}
                    onChange={(e) => setPlotId(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Drawing Revision
                  </label>
                  <NativeSelect
                    size="sm"
                    value={revision}
                    onChange={(e) => setRevision(e.target.value)}
                    className="w-full text-xs font-mono"
                  >
                    <option value="Rev 0">Rev 0 (Initial Submission)</option>
                    <option value="Rev 1">Rev 1 (First Amendment)</option>
                    <option value="Rev 2">Rev 2 (Second Amendment)</option>
                    <option value="Rev 3">Rev 3 (Final As-Built)</option>
                  </NativeSelect>
                </div>
              </div>

              <Button
                onClick={handleRunScrutiny}
                disabled={!selectedFile || isScrutinizing}
                className="w-full gap-2 text-xs font-medium"
              >
                <Sparkles className="size-3.5" />
                <span>Execute Autonomous Scrutiny</span>
              </Button>
            </div>

            {/* Quick Demo Prompts */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div
                onClick={() => {
                  setSelectedAuthority("DHA_Lahore")
                  toast.info("Selected DHA Lahore Authority", {
                    description: "Attach your PDF to audit setbacks & coverage.",
                  })
                }}
                className="rounded-lg border p-3 text-xs cursor-pointer hover:bg-muted/30 transition-colors"
              >
                <p className="font-semibold mb-1">DHA Lahore 1 Kanal</p>
                <p className="text-[11px] text-muted-foreground">
                  Verify 15 ft front and 10 ft rear setbacks plus 65% coverage limits.
                </p>
              </div>

              <div
                onClick={() => {
                  setSelectedAuthority("LDA_Lahore")
                  toast.info("Selected LDA Lahore Authority", {
                    description: "Attach your PDF to audit LDA bylaws.",
                  })
                }}
                className="rounded-lg border p-3 text-xs cursor-pointer hover:bg-muted/30 transition-colors"
              >
                <p className="font-semibold mb-1">LDA Lahore Residential</p>
                <p className="text-[11px] text-muted-foreground">
                  Audit building height, FAR ratio, and mandatory open spaces.
                </p>
              </div>

              <div
                onClick={() => {
                  setSelectedAuthority("CDA_Islamabad")
                  toast.info("Selected CDA Islamabad Authority", {
                    description: "Attach your PDF to audit CDA bylaws.",
                  })
                }}
                className="rounded-lg border p-3 text-xs cursor-pointer hover:bg-muted/30 transition-colors"
              >
                <p className="font-semibold mb-1">Structural & Safety</p>
                <p className="text-[11px] text-muted-foreground">
                  Check concrete PSI, slab thickness, and structural stability seal.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* CHAT MESSAGES STREAM */
          messages.map((msg, idx) => {
            const isUser = msg.sender === "user"

            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-4xl mx-auto ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-lg border bg-muted text-xs">
                    🏛️
                  </div>
                )}

                <div
                  className={`flex flex-col gap-1.5 max-w-3xl ${isUser
                    ? "items-end"
                    : "items-start w-full"
                    }`}
                >
                  {/* User Bubble */}
                  {isUser && (
                    <div className="group relative rounded-xl border bg-muted/50 px-4 py-2.5 text-xs text-foreground shadow-xs space-y-2">
                      {msg.file && (
                        <div className="flex items-center gap-2 pb-1 border-b border-border/50">
                          <FileText className="size-4 opacity-70" />
                          <div className="flex flex-col">
                            <span className="font-medium">{msg.file.name}</span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              {(msg.file.size / 1024 / 1024).toFixed(2)} MB • PDF Drawing Package
                            </span>
                          </div>
                        </div>
                      )}
                      {msg.text && (
                        <div className="flex items-start justify-between gap-3">
                          <p className="leading-relaxed flex-1">{msg.text}</p>
                          <button
                            type="button"
                            onClick={() => handleCopyMessage(msg.id, msg.text)}
                            className="opacity-40 group-hover:opacity-100 transition-opacity p-1 text-muted-foreground hover:text-foreground rounded hover:bg-background/80 shrink-0 cursor-pointer"
                            title="Copy message"
                          >
                            {copiedMsgId === msg.id ? (
                              <Check className="size-3 text-green-500" />
                            ) : (
                              <Copy className="size-3" />
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Assistant Report or Reply */}
                  {!isUser && (
                    <div className="w-full space-y-3">
                      {msg.verdict ? (
                        <ReportViewer
                          verdict={msg.verdict}
                          filename={msg.verdict.pdf_filename || "Drawing_Package.pdf"}
                          caseId={msg.caseId}
                          authority={selectedAuthority}
                        />
                      ) : !msg.text ? (
                        <div className="flex items-center gap-3 rounded-xl border bg-card/60 backdrop-blur-xs px-4 py-3 text-xs shadow-xs text-muted-foreground animate-pulse">
                          <div className="flex size-6 shrink-0 items-center justify-center rounded-lg border bg-muted">
                            <Sparkles className="size-3.5 animate-spin text-primary" />
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">AI is preparing response...</span>
                            <div className="flex items-center gap-1">
                              <span className="size-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:-0.3s]" />
                              <span className="size-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:-0.15s]" />
                              <span className="size-1.5 rounded-full bg-primary/70 animate-bounce" />
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="group relative rounded-xl border bg-card p-4 text-xs leading-relaxed shadow-xs">
                          <MarkdownRenderer
                            content={msg.text}
                            isStreaming={isChatLoading && idx === messages.length - 1}
                          />
                          <div className="flex items-center justify-end pt-2 border-t border-border/30 mt-3">
                            <button
                              type="button"
                              onClick={() => handleCopyMessage(msg.id, msg.text)}
                              className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors py-0.5 px-2 rounded-md hover:bg-muted/70 cursor-pointer"
                              title="Copy AI response"
                            >
                              {copiedMsgId === msg.id ? (
                                <span className="flex items-center gap-1 text-green-500 font-mono text-[10px]">
                                  <Check className="size-3" /> Copied
                                </span>
                              ) : (
                                <>
                                  <Copy className="size-3" />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <span className="text-[10px] text-muted-foreground px-1 font-mono">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                {isUser && (
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-lg border bg-primary text-primary-foreground font-semibold text-xs">
                    U
                  </div>
                )}
              </div>
            )
          })
        )}

        {/* Real-time Progressive Scrutiny Execution Indicator */}
        {isScrutinizing && (
          <div className="max-w-3xl mx-auto rounded-xl border bg-card p-5 space-y-4 shadow-xs">
            {/* Header with live timer */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b">
              <div className="flex items-center gap-3">
                <div className="relative flex size-10 shrink-0 items-center justify-center rounded-xl border border-border/80 bg-white dark:bg-white/95 p-1.5 shadow-xs">
                  <Image
                    src="/ezypro_logo.png"
                    alt="Ezypro Logo"
                    width={28}
                    height={28}
                    className="object-contain"
                  />
                  <div className="absolute -inset-0.5 rounded-xl border-2 border-transparent border-t-primary animate-spin" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold flex items-center gap-2">
                    <span>Autonomous Scrutiny Pipeline Running</span>
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Live LangGraph multi-node execution with short-term checkpointing.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 font-mono text-[11px]">
                <Badge variant="outline" className="gap-1 text-[11px]">
                  <Clock className="size-3" />
                  <span>{streamElapsed}s elapsed</span>
                </Badge>
                <Badge variant="secondary" className="text-[11px]">
                  {selectedAuthority}
                </Badge>
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={handleStopScrutiny}
                  className="h-6 px-2 text-[11px] gap-1 cursor-pointer font-medium shadow-xs"
                  title="Stop scrutiny pipeline execution (HITL)"
                >
                  <Square className="size-2.5 fill-current" />
                  <span>Stop Pipeline</span>
                </Button>
              </div>
            </div>

            {/* Live Parameter Discovery Pills */}
            {Object.keys(liveParams).length > 0 && (
              <div className="p-3 rounded-lg border bg-muted/20 space-y-1.5">
                <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="size-3" />
                  <span>Live Discovered Drawing Parameters</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-0.5">
                  {Object.entries(liveParams).map(([k, v]) => (
                    <Badge key={k} variant="outline" className="gap-1.5 text-xs font-mono py-1">
                      <span className="text-muted-foreground capitalize">{k.replace(/_/g, " ")}:</span>
                      <span className="font-semibold text-foreground">{String(v)}</span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Step-by-Step Node Timeline */}
            <div className="space-y-2.5 pt-1 text-xs">
              {pipelineStages.map((stage) => {
                const isCompleted = stage.status === "completed"
                const isRunning = stage.status === "running"

                return (
                  <div
                    key={stage.node}
                    className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${isRunning
                      ? "bg-muted/40 border-foreground/30 shadow-xs"
                      : isCompleted
                        ? "bg-card border-border/70"
                        : "opacity-40 border-dashed"
                      }`}
                  >
                    <div className="mt-0.5 shrink-0">
                      {isCompleted ? (
                        <CheckCircle2 className="size-4 text-green-500" />
                      ) : isRunning ? (
                        <RefreshCw className="size-4 animate-spin text-foreground" />
                      ) : (
                        <div className="size-3.5 rounded-full border border-muted-foreground/40 mt-0.5" />
                      )}
                    </div>
                    <div className="flex-1 space-y-0.5">
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`font-semibold ${isRunning
                            ? "text-foreground"
                            : isCompleted
                              ? "text-foreground"
                              : "text-muted-foreground"
                            }`}
                        >
                          {stage.label}
                        </span>
                        {isCompleted && stage.elapsedSeconds !== undefined && (
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {stage.elapsedSeconds}s
                          </span>
                        )}
                        {isRunning && (
                          <Badge variant="outline" className="text-[10px] animate-pulse">
                            In progress...
                          </Badge>
                        )}
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {isCompleted && stage.summary ? stage.summary : stage.defaultDesc}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Follow-up Input Bar */}
      <div className="border-t p-3 md:px-8 bg-background">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex items-center gap-2">
          {/* File attach button */}
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => fileInputRef.current?.click()}
            title="Attach new drawing PDF"
          >
            <Upload className="size-3.5" />
          </Button>

          {/* Change Model Button in Input Section */}
          <SettingsDialog
            activeModel={activeModel}
            onModelSelected={(modelId) => {
              onModelChanged?.(modelId)
            }}
            trigger={
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 px-2.5 text-xs font-mono shrink-0 hover:bg-muted/70 transition-all border-border text-foreground"
                title="Change AI Model"
              >
                <Cpu className="size-3.5 text-primary shrink-0" />
                <span className="truncate max-w-[90px] sm:max-w-[130px] font-medium">{activeModel}</span>
              </Button>
            }
          />

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="hidden"
          />

          {selectedFile && (
            <div className="flex items-center gap-1.5 rounded-md border bg-muted px-2 py-1 text-xs">
              <FileText className="size-3 shrink-0" />
              <span className="truncate max-w-[120px]">{selectedFile.name}</span>
              <Button
                type="button"
                variant="ghost"
                size="icon-xs"
                onClick={() => setSelectedFile(null)}
                className="size-4 p-0"
              >
                ×
              </Button>
            </div>
          )}

          <Input
            placeholder={
              selectedFile
                ? "Click Execute Autonomous Scrutiny above or press Enter..."
                : !currentThreadId
                  ? "Run a PDF scrutiny first to unlock chat..."
                  : "Ask about bylaws, setbacks, slab thickness, or drawing compliance..."
            }
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isScrutinizing || isChatLoading}
            className="h-9 text-xs flex-1"
          />

          {isChatLoading ? (
            <Button
              type="button"
              size="sm"
              variant="destructive"
              onClick={handleStopChatGeneration}
              className="h-8 px-2.5 gap-1.5 text-xs font-semibold cursor-pointer shadow-xs animate-pulse"
              title="Stop AI response generation (HITL)"
            >
              <Square className="size-3 fill-current" />
              <span>Stop</span>
            </Button>
          ) : (
            <Button
              type="submit"
              size="icon-sm"
              disabled={(!inputText.trim() && !selectedFile) || isScrutinizing}
            >
              <ArrowUp className="size-4" />
            </Button>
          )}
        </form>
      </div>
      {/* Floating Eye Button on Right Center of Screen to Read Final PDF */}
      {latestVerdict && (
        <div className="fixed right-0 top-1/2 -translate-y-1/2 z-40">
          <Button
            type="button"
            onClick={handleOpenPdfDialog}
            className="flex items-center gap-2 rounded-l-2xl rounded-r-none py-3.5 px-3.5 shadow-2xl bg-primary text-primary-foreground hover:bg-primary/90 border-y border-l border-primary/40 transition-all hover:-translate-x-1 cursor-pointer group"
            title="Read Final Official PDF Report"
          >
            <Eye className="size-5 transition-transform group-hover:scale-115 text-primary-foreground" />
            <span className="hidden sm:inline-block text-xs font-semibold tracking-wide pr-1">
              Read Final PDF
            </span>
          </Button>
        </div>
      )}

      {/* Final PDF Reader Modal Dialog */}
      <Dialog open={pdfDialogOpen} onOpenChange={setPdfDialogOpen}>
        <DialogContent className="sm:max-w-5xl w-[96vw] h-[88vh] flex flex-col p-4 sm:p-6 gap-3">
          <DialogHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/50 pr-8">
            <div className="flex items-center gap-2.5">
              <div className="flex size-9 items-center justify-center rounded-lg border bg-muted">
                <FileText className="size-4.5 text-primary" />
              </div>
              <div>
                <DialogTitle className="text-sm font-semibold flex items-center gap-2">
                  <span>Official Scrutiny Audit Report</span>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {selectedAuthority}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                  {latestVerdict?.pdf_filename || "Submission_Drawing.pdf"} • Verified Statutory Verdict
                </DialogDescription>
              </div>
            </div>

            {pdfUrl && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  onClick={() => window.open(pdfUrl, "_blank")}
                  title="Open PDF in new tab"
                >
                  <ExternalLink className="size-3.5" />
                  <span className="hidden sm:inline">New Tab</span>
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  className="h-8 gap-1.5 text-xs"
                  onClick={() => {
                    const link = document.createElement("a")
                    link.href = pdfUrl
                    link.setAttribute(
                      "download",
                      `Scrutiny_Report_${(latestVerdict?.pdf_filename || "Drawing").replace(/\.pdf$/i, "")}.pdf`
                    )
                    document.body.appendChild(link)
                    link.click()
                    link.remove()
                  }}
                  title="Download PDF"
                >
                  <Download className="size-3.5" />
                  <span className="hidden sm:inline">Download</span>
                </Button>
              </div>
            )}
          </DialogHeader>

          <div className="flex-1 w-full min-h-[400px] rounded-lg border bg-muted/20 overflow-hidden flex items-center justify-center relative">
            {loadingPdf ? (
              <div className="flex flex-col items-center gap-2.5 text-muted-foreground p-8">
                <RefreshCw className="size-6 animate-spin text-primary" />
                <span className="text-xs font-mono">Generating official PDF report...</span>
              </div>
            ) : pdfUrl ? (
              <iframe
                src={`${pdfUrl}#toolbar=1`}
                className="w-full h-full border-0 rounded-md"
                title="Official Scrutiny PDF Report"
              />
            ) : (
              <div className="text-xs text-muted-foreground">No PDF preview available</div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
