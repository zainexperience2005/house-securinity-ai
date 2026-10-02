"use client"

import * as React from "react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { SettingsDialog } from "@/components/settings-dialog"
import { ThemeSwitcher } from "@/components/theme-switcher"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { scrutinyApi, type ScrutinyThreadItem } from "@/lib/api"
import { toast } from "sonner"
import {
  Plus,
  Search,
  FileText,
  Trash2,
  Cpu,
  Loader2,
} from "lucide-react"

interface ScrutinySidebarProps {
  currentThreadId: string | null
  activeModel: string
  onSelectThread: (threadId: string) => void
  onNewThread: () => void
  onModelChanged: (modelId: string) => void
}

export function ScrutinySidebar({
  currentThreadId,
  activeModel,
  onSelectThread,
  onNewThread,
  onModelChanged,
}: ScrutinySidebarProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = React.useState("")
  const [deletingId, setDeletingId] = React.useState<string | null>(null)

  // Use TanStack React Query for thread caching
  const { data: threads = [], isLoading } = useQuery<ScrutinyThreadItem[]>({
    queryKey: ["threads"],
    queryFn: () => scrutinyApi.getThreads(40),
    staleTime: 1000 * 60 * 3, // 3 minutes stale time
  })

  // TanStack Mutation for thread deletion with optimistic cache update
  const deleteMutation = useMutation({
    mutationFn: (threadId: string) => scrutinyApi.deleteThread(threadId),
    onSuccess: (_, threadId) => {
      queryClient.setQueryData<ScrutinyThreadItem[]>(["threads"], (old) =>
        (old || []).filter((t) => t.thread_id !== threadId)
      )
      toast.success("Thread Deleted", {
        description: "Scrutiny session removed",
      })
      if (currentThreadId === threadId) {
        onNewThread()
      }
    },
    onError: () => {
      toast.error("Failed to delete thread")
    },
    onSettled: () => {
      setDeletingId(null)
    },
  })

  const handleDeleteThread = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    setDeletingId(threadId)
    deleteMutation.mutate(threadId)
  }

  const filteredThreads = React.useMemo(() => {
    if (!searchQuery.trim()) return threads
    const q = searchQuery.toLowerCase()
    return threads.filter(
      (t) =>
        t.thread_name.toLowerCase().includes(q) ||
        t.pdf_filename.toLowerCase().includes(q) ||
        (t.overall_verdict && t.overall_verdict.toLowerCase().includes(q))
    )
  }, [threads, searchQuery])

  const getVerdictBadge = (verdict?: string) => {
    if (!verdict) return null
    const v = verdict.toUpperCase()
    if (v.includes("PASS") || v === "COMPLIANT") {
      return (
        <Badge variant="outline" className="text-[10px] font-mono border-foreground/30">
          PASS
        </Badge>
      )
    }
    if (v.includes("FAIL") || v.includes("REJECT") || v.includes("NON_COMPLIANT")) {
      return (
        <Badge variant="default" className="text-[10px] font-mono">
          FAIL
        </Badge>
      )
    }
    if (v.includes("REVIEW") || v.includes("PENDING")) {
      return (
        <Badge variant="secondary" className="text-[10px] font-mono border">
          REVIEW
        </Badge>
      )
    }
    return (
      <Badge variant="outline" className="text-[10px] font-mono">
        {v.slice(0, 7)}
      </Badge>
    )
  }

  return (
    <aside className="flex h-screen w-72 flex-col border-r bg-sidebar text-sidebar-foreground select-none">
      {/* App Header */}
      <div className="flex flex-col gap-2 p-3.5 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg border border-border/80 bg-white dark:bg-white/95 p-1 shadow-2xs">
              <Image
                src="/ezypro_logo.png"
                alt="Ezypro Logo"
                width={24}
                height={24}
                className="object-contain"
              />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold tracking-tight text-foreground leading-none">
                House Scrutiny AI
              </span>
              <span className="text-[11px] text-muted-foreground mt-0.5">
                Drawing & Bylaw Audit
              </span>
            </div>
          </div>
          <ThemeSwitcher />
        </div>

        {/* New Audit Thread Action */}
        <Button
          variant="outline"
          size="sm"
          onClick={onNewThread}
          className="mt-2 w-full justify-start gap-2 text-xs font-medium"
        >
          <Plus className="size-3.5" />
          <span>New Scrutiny Thread</span>
        </Button>
      </div>

      <div className="px-3.5 py-1.5">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search past drawings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-7 pl-8 text-xs bg-background/50"
          />
        </div>
      </div>

      <Separator className="my-1.5" />

      {/* Threads Section */}
      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1">
        <div className="px-2 py-1 flex items-center justify-between">
          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
            Audited Drawings ({isLoading ? "…" : filteredThreads.length})
          </span>
          {isLoading && (
            <Loader2 className="size-3 animate-spin text-muted-foreground" />
          )}
        </div>

        {isLoading ? (
          /* Skeleton loading state */
          <div className="space-y-1 px-1">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex items-center gap-2 rounded-md px-2.5 py-2 animate-pulse"
              >
                <div className="size-3.5 rounded bg-muted shrink-0" />
                <div className="flex flex-col gap-1 flex-1 min-w-0">
                  <div className="h-2.5 rounded bg-muted w-3/4" />
                  <div className="h-2 rounded bg-muted/60 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredThreads.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground space-y-1">
            <FileText className="mx-auto size-6 opacity-40 mb-1" />
            <p>No scrutiny threads found.</p>
            <p className="text-[10px]">Upload a drawing to begin verification.</p>
          </div>
        ) : (
          filteredThreads.map((thread) => {
            const isSelected = thread.thread_id === currentThreadId
            const isDeleting = deletingId === thread.thread_id
            const displayName =
              thread.thread_name.length > 26
                ? thread.thread_name.slice(0, 24) + "..."
                : thread.thread_name

            const formattedTime = thread.created_at
              ? new Date(thread.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              : ""

            return (
              <div
                key={thread.thread_id}
                onClick={() => !isDeleting && onSelectThread(thread.thread_id)}
                className={`group flex items-center justify-between rounded-md px-2.5 py-2 text-xs transition-colors ${
                  isDeleting
                    ? "opacity-40 cursor-not-allowed"
                    : "cursor-pointer"
                } ${
                  isSelected
                    ? "bg-accent text-accent-foreground font-medium"
                    : "hover:bg-muted/50 text-foreground/80"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 pr-1.5">
                  <FileText className="size-3.5 shrink-0 opacity-70" />
                  <div className="flex flex-col min-w-0">
                    <span className="truncate">{displayName}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      {thread.authority || "DHA"} • {formattedTime}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  {getVerdictBadge(thread.overall_verdict)}
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={(e) => handleDeleteThread(e, thread.thread_id)}
                    disabled={isDeleting}
                    className="opacity-0 group-hover:opacity-100 transition-opacity hover:text-destructive"
                    title="Delete thread"
                  >
                    {isDeleting ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Trash2 className="size-3" />
                    )}
                  </Button>
                </div>
              </div>
            )
          })
        )}
      </div>

      <Separator />

      {/* Sidebar Footer */}
      <div className="p-3 bg-sidebar-accent/20 flex flex-col gap-2">
        {/* Active Model Indicator */}
        <div className="flex items-center justify-between px-1 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-1.5 truncate">
            <Cpu className="size-3.5 shrink-0" />
            <span className="truncate font-mono">{activeModel}</span>
          </div>
          <Badge variant="outline" className="text-[9px] px-1 py-0 uppercase">
            Active
          </Badge>
        </div>

        {/* Settings Dialog Trigger */}
        <SettingsDialog
          activeModel={activeModel}
          onModelSelected={onModelChanged}
        />
      </div>
    </aside>
  )
}
