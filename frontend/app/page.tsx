"use client"

import * as React from "react"
import { useRouter, useSearchParams, usePathname } from "next/navigation"
import { ScrutinySidebar } from "@/components/scrutiny-sidebar"
import { ChatInterface } from "@/components/chat-interface"
import { scrutinyApi } from "@/lib/api"

function ScrutinyApp() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // Read initial thread_id from URL query params
  const threadIdFromUrl = searchParams.get("thread_id")
  const [currentThreadId, setCurrentThreadId] = React.useState<string | null>(threadIdFromUrl)
  const [activeModel, setActiveModel] = React.useState("gpt-4o-2024-08-06")

  // Restore thread from localStorage if URL has no thread_id
  React.useEffect(() => {
    if (!threadIdFromUrl) {
      try {
        const saved = localStorage.getItem("hs_active_thread")
        if (saved) {
          handleSelectThread(saved)
        }
      } catch {}
    }
  }, [])

  // Sync state if user navigates back/forward in browser history
  React.useEffect(() => {
    setCurrentThreadId(threadIdFromUrl)
  }, [threadIdFromUrl])

  React.useEffect(() => {
    // Fetch default active system model from backend
    scrutinyApi
      .getModels()
      .then((res) => {
        if (res?.active_system_model) {
          setActiveModel(res.active_system_model)
        }
      })
      .catch(() => {})
  }, [])

  const handleSelectThread = (threadId: string) => {
    setCurrentThreadId(threadId)
    try {
      localStorage.setItem("hs_active_thread", threadId)
    } catch {}
    // Update the URL without a full page reload so state persists across refreshes
    const params = new URLSearchParams(searchParams.toString())
    params.set("thread_id", threadId)
    router.push(`${pathname}?${params.toString()}`)
  }

  const handleNewThread = () => {
    setCurrentThreadId(null)
    try {
      localStorage.removeItem("hs_active_thread")
    } catch {}
    // Clear thread_id from URL
    const params = new URLSearchParams(searchParams.toString())
    params.delete("thread_id")
    const newQuery = params.toString()
    router.push(newQuery ? `${pathname}?${newQuery}` : pathname)
  }

  const handleModelChanged = (modelId: string) => {
    setActiveModel(modelId)
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <ScrutinySidebar
        currentThreadId={currentThreadId}
        activeModel={activeModel}
        onSelectThread={handleSelectThread}
        onNewThread={handleNewThread}
        onModelChanged={handleModelChanged}
      />
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        <ChatInterface
          currentThreadId={currentThreadId}
          activeModel={activeModel}
          onThreadCreated={handleSelectThread}
          onModelChanged={handleModelChanged}
        />
      </main>
    </div>
  )
}

import { LoadingScreen } from "@/components/loading-screen"

export default function Page() {
  return (
    <React.Suspense fallback={<LoadingScreen />}>
      <ScrutinyApp />
    </React.Suspense>
  )
}
