"use client"

import * as React from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Check, Copy } from "lucide-react"
import { cn } from "@/lib/utils"

interface MarkdownRendererProps {
  content: string
  className?: string
  isStreaming?: boolean
}

function CodeBlock({
  inline,
  className,
  children,
  ...props
}: {
  inline?: boolean
  className?: string
  children?: React.ReactNode
} & React.HTMLAttributes<HTMLElement>) {
  const [copied, setCopied] = React.useState(false)
  const match = /language-(\w+)/.exec(className || "")
  const codeString = String(children).replace(/\n$/, "")

  if (inline) {
    return (
      <code
        className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] font-semibold text-foreground border border-border/50"
        {...props}
      >
        {children}
      </code>
    )
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-2.5 rounded-lg border border-border/60 bg-muted/40 overflow-hidden font-mono text-[11px]">
      <div className="flex items-center justify-between px-3 py-1 bg-muted/70 border-b border-border/40 text-[10px] text-muted-foreground select-none">
        <span>{match ? match[1] : "code"}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-foreground transition-colors cursor-pointer py-0.5 px-1 rounded hover:bg-background/60"
          title="Copy code"
        >
          {copied ? <Check className="size-3 text-green-500" /> : <Copy className="size-3" />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <div className="p-3 overflow-x-auto text-foreground/90 leading-relaxed">
        <pre className="m-0 p-0 bg-transparent">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      </div>
    </div>
  )
}

export function MarkdownRenderer({
  content,
  className,
  isStreaming = false,
}: MarkdownRendererProps) {
  return (
    <div className={cn("markdown-body text-xs leading-relaxed space-y-2 select-text", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-foreground mt-3 mb-1.5 pb-1 border-b border-border/40 flex items-center gap-1.5">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-semibold text-foreground mt-2.5 mb-1 pb-0.5 border-b border-border/30">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-semibold text-foreground mt-2 mb-1">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-muted-foreground mt-1.5 mb-0.5">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="leading-relaxed my-1 text-foreground/95">{children}</p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => <em className="italic text-foreground/90">{children}</em>,
          ul: ({ children }) => (
            <ul className="list-disc pl-4 space-y-1 my-1.5 text-foreground/90 marker:text-muted-foreground">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-4 space-y-1 my-1.5 text-foreground/90 marker:text-muted-foreground">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-relaxed pl-0.5">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/60 pl-3 my-2 italic text-muted-foreground bg-muted/20 py-1 rounded-r-md">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="border-border/50 my-2.5" />,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary font-medium underline underline-offset-2 hover:opacity-80 transition-opacity"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="my-2.5 overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full text-left border-collapse text-xs">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/60 border-b border-border/60 text-foreground font-semibold">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border/40 bg-card/40">{children}</tbody>
          ),
          tr: ({ children }) => <tr className="hover:bg-muted/20 transition-colors">{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-1.5 font-semibold text-[11px] text-foreground font-mono">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-1.5 text-xs text-foreground/90 align-top">
              {children}
            </td>
          ),
          code: CodeBlock,
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-primary animate-pulse align-middle" />
      )}
    </div>
  )
}
