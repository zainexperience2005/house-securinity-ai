"use client"

import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { NativeSelect } from "@/components/ui/native-select"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { scrutinyApi, type AIModel } from "@/lib/api"
import { toast } from "sonner"
import {
  Settings2,
  Check,
  Plus,
  Trash2,
  Cpu,
  ShieldCheck,
  RefreshCw,
} from "lucide-react"

interface SettingsDialogProps {
  activeModel: string
  onModelSelected: (modelId: string) => void
  trigger?: React.ReactNode
}

export function SettingsDialog({
  activeModel,
  onModelSelected,
  trigger,
}: SettingsDialogProps) {
  const queryClient = useQueryClient()
  const [open, setOpen] = React.useState(false)

  // New Model Form State
  const [newProvider, setNewProvider] = React.useState("OpenAI")
  const [newModelId, setNewModelId] = React.useState("")
  const [newModelName, setNewModelName] = React.useState("")
  const [newInputPrice, setNewInputPrice] = React.useState("2.50")
  const [newOutputPrice, setNewOutputPrice] = React.useState("10.00")
  const [newContextWindow, setNewContextWindow] = React.useState("128000")
  const [submittingModel, setSubmittingModel] = React.useState(false)

  // TanStack React Query: Cached Models
  const {
    data: modelsData,
    isLoading: loading,
    refetch: fetchModelsData,
  } = useQuery({
    queryKey: ["models"],
    queryFn: () => scrutinyApi.getModels(),
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  })

  // TanStack React Query: Cached Providers
  const { data: providers = ["OpenAI", "Anthropic", "Google", "DeepSeek", "Custom"] } =
    useQuery({
      queryKey: ["providers"],
      queryFn: () => scrutinyApi.getProviders(),
      staleTime: 1000 * 60 * 10,
    })

  const models: AIModel[] = modelsData?.models || []

  const handleSelectModel = async (modelId: string) => {
    try {
      await scrutinyApi.selectModel(modelId)
      onModelSelected(modelId)
      toast.success("Active Model Switched", {
        description: `Pipeline is now using ${modelId}`,
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Internal server error"
      toast.error("Failed to switch model", {
        description: msg,
      })
    }
  }

  const handleRegisterModel = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newModelId.trim() || !newModelName.trim()) {
      toast.error("Missing Information", {
        description: "Please specify both Model ID and Display Name",
      })
      return
    }

    setSubmittingModel(true)
    try {
      await scrutinyApi.addModel({
        provider: newProvider,
        model_id: newModelId.trim(),
        model_name: newModelName.trim(),
        input_price_per_1m: parseFloat(newInputPrice) || 0,
        output_price_per_1m: parseFloat(newOutputPrice) || 0,
        supports_vision: true,
        supports_text: true,
        context_window: parseInt(newContextWindow, 10) || 128000,
        is_default: false,
      })

      toast.success("Model Registered", {
        description: `${newModelName} added to PostgreSQL catalog`,
      })

      // Reset form and refresh list
      setNewModelId("")
      setNewModelName("")
      await fetchModelsData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not save model"
      toast.error("Registration Failed", {
        description: msg,
      })
    } finally {
      setSubmittingModel(false)
    }
  }

  const handleDeleteModel = async (modelId: string) => {
    try {
      await scrutinyApi.deleteModel(modelId)
      toast.success("Model Deleted", {
        description: `${modelId} removed from catalog`,
      })
      await fetchModelsData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Could not delete this model"
      toast.error("Deletion Failed", {
        description: msg,
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          trigger ? (
            React.isValidElement(trigger) ? trigger : <span>{trigger}</span>
          ) : (
            <Button variant="outline" size="sm" className="gap-2 w-full justify-start">
              <Settings2 className="size-4" />
              <span>Settings & Models</span>
            </Button>
          )
        }
      />
      <DialogContent className="max-w-2xl sm:max-w-2xl p-6">
        <DialogHeader className="gap-1">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Cpu className="size-5" />
            <span>AI Scrutiny Configuration & Models</span>
          </DialogTitle>
          <DialogDescription>
            Manage active multimodal vision models, register custom LLM endpoints, and inspect authority rulesets.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="models" className="mt-4 w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="models">Vision Models</TabsTrigger>
            <TabsTrigger value="add">Add Model</TabsTrigger>
            <TabsTrigger value="bylaws">Bylaws Catalog</TabsTrigger>
          </TabsList>

          {/* TAB 1: Models Catalog */}
          <TabsContent value="models" className="space-y-4 pt-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Showing {models.length} registered models in database
              </span>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => fetchModelsData()}
                disabled={loading}
                className="gap-1 text-xs"
              >
                <RefreshCw className={`size-3 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </div>

            <div className="max-h-[340px] space-y-2 overflow-y-auto pr-1">
              {loading ? (
                /* Skeleton loader while models are fetching */
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-lg border p-3 animate-pulse"
                    >
                      <div className="flex flex-col gap-2 flex-1 min-w-0 pr-3">
                        <div className="flex items-center gap-2">
                          <div className="h-3.5 rounded bg-muted w-40" />
                          <div className="h-3.5 rounded bg-muted/60 w-16" />
                        </div>
                        <div className="h-2.5 rounded bg-muted/50 w-56" />
                      </div>
                      <div className="h-7 rounded bg-muted w-16 shrink-0" />
                    </div>
                  ))}
                </div>
              ) : (
              <>
              {models.map((m) => {
                const isActive = m.model_id === activeModel
                return (
                  <div
                    key={m.model_id}
                    className={`flex items-center justify-between rounded-lg border p-3 transition-colors ${
                      isActive
                        ? "border-foreground/40 bg-muted/40 font-medium"
                        : "border-border hover:bg-muted/20"
                    }`}
                  >
                    <div className="flex flex-col gap-1 min-w-0 pr-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold truncate">
                          {m.model_name}
                        </span>
                        <Badge variant="outline" className="text-[10px] uppercase font-mono">
                          {m.provider}
                        </Badge>
                        {isActive && (
                          <Badge variant="default" className="text-[10px]">
                            Active System Model
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                        <span>ID: {m.model_id}</span>
                        <span>•</span>
                        <span>
                          ${m.input_price_per_1m.toFixed(2)} in / ${m.output_price_per_1m.toFixed(2)} out (1M)
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {isActive ? (
                        <Button variant="secondary" size="xs" disabled className="gap-1">
                          <Check className="size-3" />
                          Selected
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => handleSelectModel(m.model_id)}
                        >
                          Select
                        </Button>
                      )}
                      {!m.is_default && (
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => handleDeleteModel(m.model_id)}
                          className="text-muted-foreground hover:text-foreground"
                          title="Delete model"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
              </>
              )}
            </div>
          </TabsContent>

          {/* TAB 2: Add Model */}
          <TabsContent value="add" className="pt-3">
            <form onSubmit={handleRegisterModel} className="space-y-3.5">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="provider" className="text-xs">
                    Provider
                  </Label>
                  <NativeSelect
                    id="provider"
                    value={newProvider}
                    onChange={(e) => setNewProvider(e.target.value)}
                    className="w-full"
                  >
                    {providers.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                    <option value="Custom">Custom Provider</option>
                  </NativeSelect>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="model-id" className="text-xs">
                    Model Identifier (API ID)
                  </Label>
                  <Input
                    id="model-id"
                    placeholder="e.g. gpt-4o-2024-08-06"
                    value={newModelId}
                    onChange={(e) => setNewModelId(e.target.value)}
                    required
                    className="h-8 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="model-name" className="text-xs">
                  Display Name
                </Label>
                <Input
                  id="model-name"
                  placeholder="e.g. GPT-4o Vision High Resolution"
                  value={newModelName}
                  onChange={(e) => setNewModelName(e.target.value)}
                  required
                  className="h-8 text-xs"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="input-price" className="text-xs">
                    Input $/1M Tokens
                  </Label>
                  <Input
                    id="input-price"
                    type="number"
                    step="0.01"
                    value={newInputPrice}
                    onChange={(e) => setNewInputPrice(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="output-price" className="text-xs">
                    Output $/1M Tokens
                  </Label>
                  <Input
                    id="output-price"
                    type="number"
                    step="0.01"
                    value={newOutputPrice}
                    onChange={(e) => setNewOutputPrice(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="ctx-window" className="text-xs">
                    Context Window
                  </Label>
                  <Input
                    id="ctx-window"
                    type="number"
                    value={newContextWindow}
                    onChange={(e) => setNewContextWindow(e.target.value)}
                    className="h-8 text-xs font-mono"
                  />
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground pt-1">
                Note: Scrutiny pipeline mandates multimodal vision & CAD geometry understanding capabilities.
              </p>

              <div className="pt-2 flex justify-end">
                <Button type="submit" size="sm" disabled={submittingModel} className="gap-1.5">
                  <Plus className="size-3.5" />
                  {submittingModel ? "Registering..." : "Add Vision Model"}
                </Button>
              </div>
            </form>
          </TabsContent>

          {/* TAB 3: Bylaws Catalog */}
          <TabsContent value="bylaws" className="space-y-3 pt-3">
            <div className="rounded-lg border p-4 text-xs space-y-2">
              <div className="flex items-center gap-2 font-medium text-sm">
                <ShieldCheck className="size-4" />
                <span>Supported Municipal Authorities</span>
              </div>
              <p className="text-muted-foreground leading-relaxed">
                House Scrutiny AI maintains codified statutory setback, FAR, ground coverage, and seismic reinforcement regulations for:
              </p>
              <div className="grid grid-cols-2 gap-2 pt-2">
                <div className="p-2.5 rounded-md border bg-muted/20">
                  <p className="font-semibold">DHA Lahore</p>
                  <p className="text-[11px] text-muted-foreground">Defence Housing Authority Building Regulations 2024</p>
                </div>
                <div className="p-2.5 rounded-md border bg-muted/20">
                  <p className="font-semibold">LDA Lahore</p>
                  <p className="text-[11px] text-muted-foreground">Lahore Development Authority Building Regulations</p>
                </div>
                <div className="p-2.5 rounded-md border bg-muted/20">
                  <p className="font-semibold">CDA Islamabad</p>
                  <p className="text-[11px] text-muted-foreground">Capital Development Authority Islamabad Bylaws</p>
                </div>
                <div className="p-2.5 rounded-md border bg-muted/20">
                  <p className="font-semibold">Bahria Town</p>
                  <p className="text-[11px] text-muted-foreground">Bahria Town Design & Construction Bylaws</p>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
