import * as React from "react"
import Image from "next/image"

interface LoadingScreenProps {
  title?: string
  subtitle?: string
}

export function LoadingScreen({
  title = "House Scrutiny AI",
  subtitle = "Loading House Scrutiny AI...",
}: LoadingScreenProps) {
  return (
    <div className="h-screen w-full bg-background flex flex-col items-center justify-center gap-4 select-none animate-in fade-in-50 duration-300">
      <div className="relative flex items-center justify-center">
        {/* Subtle glowing halo */}
        <div className="absolute -inset-3 rounded-3xl bg-primary/10 blur-xl animate-pulse" />

        {/* Logo Card */}
        <div className="relative flex size-20 items-center justify-center rounded-2xl border border-border/80 bg-white dark:bg-white/95 shadow-md p-3">
          <Image
            src="/ezypro_logo.png"
            alt="Ezypro Logo"
            width={60}
            height={60}
            priority
            className="object-contain"
          />
        </div>

        {/* Orbiting spinner ring */}
        <div className="absolute -inset-1.5 rounded-3xl border-2 border-transparent border-t-primary border-r-primary/50 animate-spin" />
      </div>

      <div className="flex flex-col items-center text-center gap-1.5 max-w-xs px-4">
        <h2 className="text-sm font-semibold tracking-tight text-foreground">
          {title}
        </h2>
        <div className="flex items-center gap-2">
          <span className="size-1.5 rounded-full bg-primary animate-ping" />
          <span className="text-xs text-muted-foreground font-mono">
            {subtitle}
          </span>
        </div>
      </div>
    </div>
  )
}
