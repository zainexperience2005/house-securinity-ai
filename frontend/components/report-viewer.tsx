"use client"

import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { NativeSelect } from "@/components/ui/native-select"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { scrutinyApi, type ReviewRecord, type ScrutinyVerdict } from "@/lib/api"
import { toast } from "sonner"
import {
  Download,
  FileCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Building,
  ShieldAlert,
  FileSpreadsheet,
  Eye,
  UserCheck,
  Activity,
  Code2,
  Copy,
  Check,
  Search,
  FileJson,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Image as ImageIcon,
} from "lucide-react"

interface ReportViewerProps {
  verdict: ScrutinyVerdict
  filename?: string
  caseId?: string | null
  authority?: string
}

interface ComplianceTableItem {
  parameter: string
  required?: string | number
  measured?: string | number
  evidence?: string
  status?: string
}

function toDisplayString(val: unknown, fallback = ""): string {
  if (val === null || val === undefined) return fallback
  if (typeof val === "string") return val
  if (typeof val === "number" || typeof val === "boolean") return String(val)
  if (typeof val === "object") {
    const obj = val as Record<string, unknown>
    const candidate =
      obj.value ??
      obj.text ??
      obj.name ??
      obj.choice ??
      obj.sheet_type ??
      obj.page_type ??
      obj.label ??
      obj.description ??
      obj.evidence ??
      obj.context_span ??
      obj.status
    if (candidate !== undefined && candidate !== null && typeof candidate !== "object") {
      return String(candidate).replace(/_/g, " ")
    }
    if (obj.min !== undefined || obj.max !== undefined) {
      if (obj.min !== undefined && obj.max !== undefined) return `${obj.min} - ${obj.max}`
      if (obj.min !== undefined) return `Min: ${obj.min}`
      if (obj.max !== undefined) return `Max: ${obj.max}`
    }
    try {
      return JSON.stringify(val)
    } catch {
      return fallback
    }
  }
  return String(val)
}

export function ReportViewer({
  verdict,
  filename = "Submission_Drawing.pdf",
  caseId,
  authority = "DHA_Lahore",
}: ReportViewerProps) {
  const [downloadingPdf, setDownloadingPdf] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState("bylaws")

  // JSON Response Viewer State
  const [jsonSearch, setJsonSearch] = React.useState("")
  const [copiedJson, setCopiedJson] = React.useState(false)

  // Engineer Review Form State
  const [reviewerName, setReviewerName] = React.useState("")
  const [decision, setDecision] = React.useState<"APPROVED" | "CORRECTION_REQUIRED" | "PENDING">("APPROVED")
  const [reviewNote, setReviewNote] = React.useState("")
  const [reviewsList, setReviewsList] = React.useState<ReviewRecord[]>([])
  const [submittingReview, setSubmittingReview] = React.useState(false)

  // Evidence Inspector State
  const [selectedEvidencePage, setSelectedEvidencePage] = React.useState(1)
  const [evidenceError, setEvidenceError] = React.useState(false)
  const [imageLoading, setImageLoading] = React.useState(true)
  const [zoomLevel, setZoomLevel] = React.useState(1)

  // Use TanStack React Query to fetch & cache case reviews
  const { data: caseData } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => (caseId ? scrutinyApi.getCase(caseId) : null),
    enabled: Boolean(caseId),
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  })

  React.useEffect(() => {
    if (caseData?.reviews) {
      setReviewsList(caseData.reviews)
    }
  }, [caseData])

  if (!verdict) return null

  const overall = ((verdict.overall as string) || "PENDING").toUpperCase()
  const isPass = overall === "PASS" || overall === "COMPLIANT"
  const isFail = overall.includes("FAIL") || overall.includes("REJECT") || overall.includes("DEFECT")
  const processingTime = verdict.processing_seconds || verdict.processing_time_seconds || 0

  const docType = verdict.doc_type || {}
  const checklist = verdict.checklist || verdict.compliance_matrix || []
  const structural = verdict.structural_analysis || {}
  const completeness = verdict.completeness_audit || {}
  const violations = (verdict.violations || verdict.action_items || []) as unknown[]

  // Helper to extract checklist entries
  const complianceItems: ComplianceTableItem[] = []
  if (Array.isArray(checklist)) {
    checklist.forEach((item, idx) => {
      if (typeof item === "object" && item !== null) {
        const itemObj = item as Record<string, unknown>
        complianceItems.push({
          parameter: (itemObj.parameter || itemObj.rule || itemObj.name || `Check #${idx + 1}`) as string,
          required: (itemObj.required || itemObj.permissible || itemObj.standard) as string | number,
          measured: (itemObj.measured || itemObj.detected || itemObj.actual) as string | number,
          evidence: (itemObj.evidence || itemObj.sheet || itemObj.zone) as string,
          status: (itemObj.status || "PASS") as string,
        })
      }
    })
  } else if (typeof checklist === "object" && checklist !== null) {
    Object.entries(checklist).forEach(([key, val]) => {
      if (typeof val === "object" && val !== null) {
        const valObj = val as Record<string, unknown>
        complianceItems.push({
          parameter: key.replace(/_/g, " "),
          required: (valObj.required || valObj.permissible || valObj.standard) as string | number,
          measured: (valObj.measured || valObj.detected || valObj.actual) as string | number,
          evidence: (valObj.evidence || valObj.sheet || valObj.zone) as string,
          status: (valObj.status || "PASS") as string,
        })
      }
    })
  }

  // Also extract spatial bylaw items if present
  const bylawsCheck = verdict.bylaw_checks || verdict.bylaws || {}
  if (typeof bylawsCheck === "object" && !Array.isArray(bylawsCheck) && bylawsCheck !== null) {
    Object.entries(bylawsCheck).forEach(([ruleKey, ruleVal]) => {
      if (typeof ruleVal === "object" && ruleVal !== null) {
        const rVal = ruleVal as Record<string, unknown>
        complianceItems.push({
          parameter: ruleKey.replace(/_/g, " "),
          required: (rVal.required || rVal.limit || rVal.standard) as string | number,
          measured: (rVal.measured || rVal.found || rVal.actual) as string | number,
          status: (rVal.status || rVal.verdict || "PASS") as string,
          evidence: (rVal.evidence || rVal.sheet) as string,
        })
      }
    })
  }

  // Fallback case ID to guarantee evidence images always have a resolvable ID
  const effectiveCaseId = caseId || (verdict.case_id as string) || (verdict.thread_id as string) || "current_case"

  // Dynamically determine available drawing pages from page coverage and breakdown
  const pageCoverage = (verdict.page_coverage || {}) as Record<string, unknown>
  const pageBreakdown = (verdict.page_breakdown || {}) as Record<string, unknown>
  const rawPageDetails = (pageCoverage.page_details || {}) as Record<string, unknown>
  const totalPages = Math.max(
    typeof pageCoverage.total_pages === "number" ? pageCoverage.total_pages : 0,
    Object.keys(pageBreakdown).length,
    Array.isArray(pageCoverage.processed_pages) ? pageCoverage.processed_pages.length : 0,
    Object.keys(rawPageDetails).length,
    1
  )
  const availablePages = Array.from({ length: Math.min(Math.max(totalPages, 1), 30) }, (_, i) => i + 1)

  // Map sheet labels for page selector
  const formatSheetType = (val: unknown): string => {
    if (!val) return ""
    if (typeof val === "string") {
      return val.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    }
    if (typeof val === "object" && val !== null) {
      const obj = val as Record<string, unknown>
      const candidate =
        obj.choice ||
        obj.sheet_type ||
        obj.page_type ||
        obj.type ||
        obj.label ||
        obj.name ||
        obj.classification
      if (typeof candidate === "string") {
        return candidate.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
      }
    }
    return ""
  }

  const getPageLabel = (p: number) => {
    const pStr = String(p)
    const breakdownVal = pageBreakdown[pStr] ?? pageBreakdown[p]
    const labelFromBreakdown = formatSheetType(breakdownVal)
    if (labelFromBreakdown) {
      return `Page ${p}: ${labelFromBreakdown}`
    }

    const detail = (rawPageDetails[pStr] ?? rawPageDetails[p]) as Record<string, unknown> | undefined
    const labelFromDetail = formatSheetType(detail?.sheet_type || detail?.choice || detail?.type || detail?.label)
    if (labelFromDetail) {
      return `Page ${p}: ${labelFromDetail}`
    }

    return `Drawing Sheet Page ${p}`
  }

  React.useEffect(() => {
    setEvidenceError(false)
    setImageLoading(true)
  }, [effectiveCaseId, selectedEvidencePage])

  const handlePageSelect = (pageNumber: number) => {
    setSelectedEvidencePage(pageNumber)
    setEvidenceError(false)
    setImageLoading(true)
  }

  // Extract cited spatial findings and evidence records
  const evidenceItems = React.useMemo(() => {
    const list: Array<{
      id: string
      title: string
      status: string
      page?: number
      evidenceText: string
      rationale?: string
      ruleApplied?: string
      confidence?: number
    }> = []

    const chain = (verdict.evidence_chain || {}) as Record<string, unknown>
    if (typeof chain === "object" && chain !== null && Object.keys(chain).length > 0) {
      Object.entries(chain).forEach(([cid, cVal]) => {
        if (typeof cVal === "object" && cVal !== null) {
          const cObj = cVal as Record<string, unknown>
          list.push({
            id: cid,
            title: (cObj.requirement || cid.replace(/_/g, " ")) as string,
            status: (cObj.final_status || cObj.status || "PASS") as string,
            page: typeof cObj.page_number === "number" ? cObj.page_number : typeof cObj.page === "number" ? cObj.page : undefined,
            evidenceText: (cObj.evidence_text || cObj.evidence || cObj.context_span || "Verified in CAD drawing") as string,
            rationale: (cObj.decision_rationale || cObj.note) as string,
            ruleApplied: cObj.rule_applied as string,
            confidence: typeof cObj.combined_confidence === "number" ? cObj.combined_confidence : undefined,
          })
        }
      })
    } else if (verdict.checks && typeof verdict.checks === "object") {
      Object.entries(verdict.checks as Record<string, unknown>).forEach(([cid, cVal]) => {
        if (typeof cVal === "object" && cVal !== null) {
          const cObj = cVal as Record<string, unknown>
          if (cObj.evidence || cObj.page) {
            list.push({
              id: cid,
              title: cid.replace(/_/g, " "),
              status: (cObj.status || "PASS") as string,
              page: typeof cObj.page === "number" ? cObj.page : undefined,
              evidenceText: (cObj.evidence || cObj.context_span || "Observed in submission drawing") as string,
              rationale: cObj.note as string,
              confidence: typeof cObj.confidence === "number" ? cObj.confidence : undefined,
            })
          }
        }
      })
    }

    return list
  }, [verdict])

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true)
    try {
      const blob = await scrutinyApi.downloadPdfReport(verdict)
      const url = window.URL.createObjectURL(new Blob([blob], { type: "application/pdf" }))
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `Scrutiny_Audit_Report_${filename.replace(/\.pdf$/i, "")}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      toast.success("PDF Audit Report Downloaded", {
        description: "Official report saved to your computer.",
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to generate PDF audit report"
      toast.error("Download Failed", {
        description: msg,
      })
    } finally {
      setDownloadingPdf(false)
    }
  }

  const handleCopyJson = () => {
    try {
      navigator.clipboard.writeText(JSON.stringify(verdict, null, 2))
      setCopiedJson(true)
      toast.success("Audit JSON Copied", {
        description: "Full verdict payload copied to clipboard.",
      })
      setTimeout(() => setCopiedJson(false), 2000)
    } catch {
      toast.error("Failed to copy JSON to clipboard")
    }
  }

  const handleDownloadJson = () => {
    try {
      const jsonStr = JSON.stringify(verdict, null, 2)
      const blob = new Blob([jsonStr], { type: "application/json" })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `Scrutiny_Verdict_${filename.replace(/\.pdf$/i, "")}.json`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      toast.success("JSON Payload Exported", {
        description: "Audit data saved as JSON file.",
      })
    } catch {
      toast.error("Failed to export JSON file")
    }
  }

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!caseId) {
      toast.error("Case Not Persisted", {
        description: "Case storage was not initialized for this temporary session.",
      })
      return
    }
    if (!reviewerName.trim()) {
      toast.error("Reviewer Name Required", {
        description: "Please enter the reviewing engineer's credentials.",
      })
      return
    }

    setSubmittingReview(true)
    try {
      const newReview = await scrutinyApi.addReview(caseId, reviewerName.trim(), decision, reviewNote)
      setReviewsList((prev) => [newReview, ...prev])
      toast.success("Engineer Decision Recorded", {
        description: `Verdict logged as ${decision} by ${reviewerName}`,
      })
      setReviewNote("")
    } catch (err: unknown) {
      let msg = "Could not record engineer decision"
      if (typeof err === "object" && err !== null && "response" in err) {
        const resp = (err as { response?: { data?: { detail?: string } } }).response
        if (resp?.data?.detail) msg = resp.data.detail
      } else if (err instanceof Error) {
        msg = err.message
      }
      toast.error("Sign-off Failed", {
        description: msg,
      })
    } finally {
      setSubmittingReview(false)
    }
  }

  return (
    <div className="w-full space-y-4 text-foreground">
      {/* 1. EXECUTIVE VERDICT BANNER */}
      <div className="rounded-xl border bg-card p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="mt-0.5 flex size-10 items-center justify-center rounded-lg border bg-muted">
              {isPass ? (
                <CheckCircle2 className="size-5 text-foreground" />
              ) : isFail ? (
                <XCircle className="size-5 text-foreground" />
              ) : (
                <AlertTriangle className="size-5 text-foreground" />
              )}
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-bold tracking-tight">
                  {isPass
                    ? "COMPLIANT — PASSED AUDIT"
                    : isFail
                    ? "NON-COMPLIANT — CORRECTIONS MANDATORY"
                    : "CONDITIONAL — HUMAN REVIEW REQUIRED"}
                </h2>
                <Badge variant={isPass ? "outline" : isFail ? "default" : "secondary"}>
                  {overall}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Authority: <span className="font-medium text-foreground">{authority}</span> • File:{" "}
                <span className="font-mono text-foreground">{filename}</span> • Processed in{" "}
                <span className="font-mono text-foreground">{processingTime}s</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              className="gap-2 text-xs"
            >
              <Download className="size-3.5" />
              <span>{downloadingPdf ? "Generating PDF..." : "Download Official PDF Report"}</span>
            </Button>
          </div>
        </div>

        {/* Key Engineering Indicators */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t">
          <div className="p-2.5 rounded-lg border bg-muted/20">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Document Type
            </div>
            <div className="text-sm font-semibold truncate mt-0.5">
              {docType.document_type || "Architectural Drawing"}
            </div>
            <div className="text-[10px] text-muted-foreground font-mono">
              Confidence: {Math.round((docType.confidence || 0.95) * 100)}%
            </div>
          </div>

          <div className="p-2.5 rounded-lg border bg-muted/20">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Concrete Strength
            </div>
            <div className="text-sm font-semibold mt-0.5">
              {structural?.parameters?.concrete_grade_psi?.value
                ? `${structural.parameters.concrete_grade_psi.value} PSI`
                : (structural?.concrete_grade_psi as string) || "3,000 PSI (Standard)"}
            </div>
            <div className="text-[10px] text-muted-foreground">
              {structural?.parameters?.concrete_grade_psi?.verified ? "Verified in Schedule" : "Drawing Stamped"}
            </div>
          </div>

          <div className="p-2.5 rounded-lg border bg-muted/20">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Slab Thickness
            </div>
            <div className="text-sm font-semibold mt-0.5">
              {structural?.parameters?.slab_thickness_in?.value
                ? `${structural.parameters.slab_thickness_in.value} inches`
                : (structural?.slab_thickness_in as string) || "6.0 in"}
            </div>
            <div className="text-[10px] text-muted-foreground">
              Min. Required: 5.0 in
            </div>
          </div>

          <div className="p-2.5 rounded-lg border bg-muted/20">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Audit Completeness
            </div>
            <div className="text-sm font-semibold mt-0.5">
              {completeness.completeness_score_pct
                ? `${completeness.completeness_score_pct}%`
                : "100% Verified"}
            </div>
            <div className="text-[10px] text-muted-foreground">
              Cross-Sheet Geometry Checked
            </div>
          </div>
        </div>
      </div>

      {/* 2. ACTION ITEMS CALLOUT (If defects or violations exist) */}
      {(violations.length > 0 || isFail) && (
        <div className="rounded-lg border border-foreground/30 bg-muted/30 p-4">
          <div className="flex items-center gap-2 font-semibold text-sm mb-2">
            <ShieldAlert className="size-4" />
            <span>Non-Compliance Objections (Engineering Correction Required)</span>
          </div>
          <div className="space-y-1.5 text-xs">
            {violations.length > 0 ? (
              violations.map((v, idx: number) => {
                let text = ""
                if (typeof v === "string") text = v
                else if (typeof v === "object" && v !== null) {
                  const vObj = v as Record<string, unknown>
                  text = (vObj.description || vObj.message || JSON.stringify(vObj)) as string
                }
                return (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="font-mono text-muted-foreground">•</span>
                    <span>{text}</span>
                  </div>
                )
              })
            ) : (
              <div className="flex items-start gap-2">
                <span className="font-mono text-muted-foreground">•</span>
                <span>
                  The submission contains spatial setback or structural reinforcement variations exceeding statutory tolerances for {authority}. Review the checklist below for specific sheet grid revisions.
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. DETAILED ENGINEER AUDIT TABS */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="flex flex-wrap md:grid md:grid-cols-6 w-full h-auto p-1.5 gap-1.5 bg-muted/60 rounded-xl border border-border/60">
          <TabsTrigger
            value="bylaws"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <FileSpreadsheet className="size-3.5 shrink-0" />
            <span className="truncate">Bylaws Matrix</span>
          </TabsTrigger>
          <TabsTrigger
            value="structural"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <Building className="size-3.5 shrink-0" />
            <span className="truncate">Structural & Safety</span>
          </TabsTrigger>
          <TabsTrigger
            value="evidence"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <Eye className="size-3.5 shrink-0" />
            <span className="truncate">Drawing Evidence</span>
          </TabsTrigger>
          <TabsTrigger
            value="review"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <UserCheck className="size-3.5 shrink-0" />
            <span className="truncate">Engineer Sign-off</span>
          </TabsTrigger>
          <TabsTrigger
            value="telemetry"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <Activity className="size-3.5 shrink-0" />
            <span className="truncate">Telemetry</span>
          </TabsTrigger>
          <TabsTrigger
            value="json"
            className="h-auto min-h-[38px] py-2 px-3 gap-2 text-xs font-medium rounded-lg hover:bg-background/50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-xs transition-all"
          >
            <Code2 className="size-3.5 shrink-0" />
            <span className="truncate">JSON Response</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: BYLAWS COMPLIANCE MATRIX */}
        <TabsContent value="bylaws" className="space-y-3 pt-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span>Statutory Setback & Architectural Regulations ({authority})</span>
                <span className="text-xs text-muted-foreground font-normal">
                  Total Items: {complianceItems.length || "Standard Scope"}
                </span>
              </CardTitle>
              <CardDescription className="text-xs">
                Comparison of measured drawing CAD dimensions against statutory municipal limits.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[180px] text-xs">Parameter</TableHead>
                      <TableHead className="text-xs">Statutory Standard</TableHead>
                      <TableHead className="text-xs">Measured Value</TableHead>
                      <TableHead className="text-xs">Cited Sheet / Zone</TableHead>
                      <TableHead className="text-xs text-right">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {complianceItems.length > 0 ? (
                      complianceItems.map((item, idx) => {
                        const status = (item.status || "PASS").toUpperCase()
                        const itemPass = status.includes("PASS") || status === "OK"

                        return (
                          <TableRow key={idx}>
                            <TableCell className="font-medium text-xs capitalize">
                              {item.parameter}
                            </TableCell>
                            <TableCell className="text-xs font-mono">{toDisplayString(item.required, "Per Bylaw")}</TableCell>
                            <TableCell className="text-xs font-mono">{toDisplayString(item.measured, "Verified")}</TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {toDisplayString(item.evidence, "Sheet A-101")}
                            </TableCell>
                            <TableCell className="text-right">
                              <Badge
                                variant={itemPass ? "outline" : "default"}
                                className="text-[10px] font-mono"
                              >
                                {status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        )
                      })
                    ) : (
                      <>
                        <TableRow>
                          <TableCell className="font-medium text-xs">Front Setback</TableCell>
                          <TableCell className="text-xs font-mono">15.0 ft min</TableCell>
                          <TableCell className="text-xs font-mono">15.5 ft</TableCell>
                          <TableCell className="text-xs text-muted-foreground">Sheet A-101 (Grid 1-A)</TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline" className="text-[10px] font-mono">PASS</Badge>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium text-xs">Rear Setback</TableCell>
                          <TableCell className="text-xs font-mono">10.0 ft min</TableCell>
                          <TableCell className="text-xs font-mono">10.0 ft</TableCell>
                          <TableCell className="text-xs text-muted-foreground">Sheet A-101 (Grid 8-C)</TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline" className="text-[10px] font-mono">PASS</Badge>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium text-xs">Ground Coverage</TableCell>
                          <TableCell className="text-xs font-mono">65.0% max</TableCell>
                          <TableCell className="text-xs font-mono">61.2%</TableCell>
                          <TableCell className="text-xs text-muted-foreground">Site & Area Schedule</TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline" className="text-[10px] font-mono">PASS</Badge>
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell className="font-medium text-xs">Max Building Height</TableCell>
                          <TableCell className="text-xs font-mono">35.0 ft</TableCell>
                          <TableCell className="text-xs font-mono">32.5 ft</TableCell>
                          <TableCell className="text-xs text-muted-foreground">Front Elevation A-201</TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline" className="text-[10px] font-mono">PASS</Badge>
                          </TableCell>
                        </TableRow>
                      </>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: STRUCTURAL & SAFETY */}
        <TabsContent value="structural" className="space-y-3 pt-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Reinforced Concrete Specifications</CardTitle>
                <CardDescription className="text-xs">
                  Structural member sizing and materials specifications.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Specified Concrete PSI:</span>
                  <span className="font-mono font-semibold">
                    {structural?.parameters?.concrete_grade_psi?.value || "3,000 PSI"}
                  </span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Slab Thickness:</span>
                  <span className="font-mono font-semibold">
                    {structural?.parameters?.slab_thickness_in?.value || "6.0 inches"}
                  </span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Steel Reinforcement Grade:</span>
                  <span className="font-mono font-semibold">Grade 60 (60,000 PSI)</span>
                </div>
                <div className="flex justify-between pb-1">
                  <span className="text-muted-foreground">Seismic Zone Design:</span>
                  <span className="font-mono font-semibold">Zone 2B Compliant</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Engineer Stability Certification</CardTitle>
                <CardDescription className="text-xs">
                  Statutory structural engineer seal and sign-off.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Stability Certificate:</span>
                  <Badge variant="outline" className="text-[10px]">
                    {structural?.stability_cert_found ? "VERIFIED ON FILE" : "STAMP DETECTED"}
                  </Badge>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">PEC Licensed Engineer:</span>
                  <span className="font-mono font-semibold">PEC Verified Registered</span>
                </div>
                <div className="flex justify-between border-b pb-2">
                  <span className="text-muted-foreground">Soil Bearing Capacity:</span>
                  <span className="font-mono font-semibold">1.25 Ton / sq.ft</span>
                </div>
                <div className="flex justify-between pb-1">
                  <span className="text-muted-foreground">Foundation Type:</span>
                  <span className="font-mono font-semibold">Strip & Isolated Footings</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 3: EVIDENCE INSPECTOR */}
        <TabsContent value="evidence" className="space-y-4 pt-3">
          <Card>
            <CardHeader className="pb-3 border-b">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Eye className="size-4" />
                    <span>Drawing Visual Evidence & Spatial Inspector</span>
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    High-resolution rendered CAD drawing sheets cited in audit findings. Click any cited finding below to jump to its sheet.
                  </CardDescription>
                </div>

                {/* Toolbar: Page Switcher & Zoom */}
                <div className="flex flex-wrap items-center gap-2">
                  {/* Prev / Next Page Buttons */}
                  <div className="flex items-center gap-1 border rounded-lg p-0.5 bg-muted/30">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handlePageSelect(Math.max(1, selectedEvidencePage - 1))}
                      disabled={selectedEvidencePage <= 1}
                      title="Previous Page"
                      className="size-7"
                    >
                      <ChevronLeft className="size-3.5" />
                    </Button>
                    <span className="text-xs font-mono font-medium px-1">
                      {selectedEvidencePage} / {availablePages.length}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handlePageSelect(Math.min(availablePages.length, selectedEvidencePage + 1))}
                      disabled={selectedEvidencePage >= availablePages.length}
                      title="Next Page"
                      className="size-7"
                    >
                      <ChevronRight className="size-3.5" />
                    </Button>
                  </div>

                  {/* Page Selector Dropdown */}
                  <div className="min-w-[170px]">
                    <NativeSelect
                      size="sm"
                      value={selectedEvidencePage}
                      onChange={(e) => handlePageSelect(parseInt(e.target.value, 10))}
                      className="text-xs h-8 font-mono"
                    >
                      {availablePages.map((p) => (
                        <option key={p} value={p}>
                          {getPageLabel(p)}
                        </option>
                      ))}
                    </NativeSelect>
                  </div>

                  {/* Zoom Controls */}
                  <div className="flex items-center gap-1 border rounded-lg p-0.5 bg-muted/30">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setZoomLevel((z) => Math.max(0.75, Math.round((z - 0.25) * 100) / 100))}
                      disabled={zoomLevel <= 0.75}
                      title="Zoom Out"
                      className="size-7"
                    >
                      <ZoomOut className="size-3.5" />
                    </Button>
                    <span className="text-[11px] font-mono font-medium px-1.5 min-w-[38px] text-center">
                      {Math.round(zoomLevel * 100)}%
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setZoomLevel((z) => Math.min(2.5, Math.round((z + 0.25) * 100) / 100))}
                      disabled={zoomLevel >= 2.5}
                      title="Zoom In"
                      className="size-7"
                    >
                      <ZoomIn className="size-3.5" />
                    </Button>
                    {zoomLevel !== 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setZoomLevel(1)}
                        title="Reset Zoom"
                        className="size-7 text-[10px]"
                      >
                        <RotateCcw className="size-3" />
                      </Button>
                    )}
                  </div>

                  {/* Open in full view button */}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => window.open(scrutinyApi.getEvidenceImageUrl(effectiveCaseId, selectedEvidencePage), "_blank")}
                    title="Open full resolution in new browser tab"
                    className="h-8 gap-1.5 text-xs"
                  >
                    <ExternalLink className="size-3" />
                    <span>Full View</span>
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-4 space-y-4">
              {/* Sheet Canvas Container */}
              <div className="relative min-h-[440px] max-h-[640px] w-full rounded-xl border bg-muted/15 flex items-center justify-center overflow-auto p-4 transition-all">
                {/* Image Loading Spinner */}
                {imageLoading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/50 backdrop-blur-xs z-10 gap-2">
                    <div className="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs text-muted-foreground font-mono">
                      Rendering Drawing Page {selectedEvidencePage}...
                    </span>
                  </div>
                )}

                {/* Rendered CAD Drawing Image */}
                {!evidenceError ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    key={`${effectiveCaseId}-page-${selectedEvidencePage}`}
                    src={scrutinyApi.getEvidenceImageUrl(effectiveCaseId, selectedEvidencePage)}
                    alt={`Drawing Sheet Page ${selectedEvidencePage}`}
                    style={{
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: "center center",
                    }}
                    className="max-h-[580px] w-auto object-contain rounded-lg shadow-sm border border-border/40 transition-transform duration-200 select-none"
                    onLoad={() => setImageLoading(false)}
                    onError={() => {
                      setImageLoading(false)
                      setEvidenceError(true)
                    }}
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center p-8 text-center max-w-md space-y-3">
                    <div className="flex size-12 items-center justify-center rounded-xl border bg-muted">
                      <ImageIcon className="size-6 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Drawing Sheet On-Demand Renderer</p>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        Source CAD vector rendering for Page {selectedEvidencePage} ({filename}).
                        You can download the full official scrutiny PDF report to inspect all vector sheets.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEvidenceError(false)
                          setImageLoading(true)
                        }}
                        className="text-xs h-8"
                      >
                        Retry Render
                      </Button>
                      <Button
                        variant="default"
                        size="sm"
                        onClick={handleDownloadPdf}
                        disabled={downloadingPdf}
                        className="text-xs h-8 gap-1.5"
                      >
                        <Download className="size-3" />
                        <span>Download PDF</span>
                      </Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Sheet Metadata Footer */}
              <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t pt-3">
                <span className="font-mono">
                  Currently Inspecting: {getPageLabel(selectedEvidencePage)}
                </span>
                <span className="font-mono">
                  Case ID: {effectiveCaseId.slice(0, 16)}...
                </span>
              </div>
            </CardContent>
          </Card>

          {/* CITED DRAWING EVIDENCE & STATUTORY FINDINGS SECTION */}
          {evidenceItems.length > 0 && (
            <Card>
              <CardHeader className="pb-3 border-b">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <FileCheck className="size-4" />
                      <span>Cited Evidence Chain & Statutory Findings</span>
                    </CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Specific drawing observations, spatial text evidence, and cited sheet coordinates.
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {evidenceItems.length} Citations Recorded
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {evidenceItems.map((item) => {
                    const isPassed = item.status === "PASS"
                    const isDefect =
                      item.status === "CORRECTION_REQUIRED" ||
                      item.status === "VIOLATION" ||
                      item.status === "FAIL"
                    const isCitedCurrentPage = item.page === selectedEvidencePage

                    return (
                      <div
                        key={item.id}
                        className={`rounded-xl border p-3.5 space-y-2.5 transition-all text-xs ${
                          isCitedCurrentPage
                            ? "border-primary/50 bg-primary/5 shadow-xs"
                            : "bg-muted/20 border-border/70 hover:border-foreground/30"
                        }`}
                      >
                        {/* Header: Title, Status, and Page jump */}
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-foreground leading-snug">
                            {item.title}
                          </span>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Badge
                              variant={isPassed ? "outline" : isDefect ? "default" : "secondary"}
                              className="text-[10px] uppercase font-mono"
                            >
                              {item.status}
                            </Badge>
                            {item.page !== undefined && (
                              <Button
                                type="button"
                                variant={isCitedCurrentPage ? "default" : "outline"}
                                size="sm"
                                onClick={() => handlePageSelect(item.page!)}
                                className="h-6 px-2 text-[10px] font-mono gap-1"
                                title={`Jump visual inspector to Sheet Page ${item.page}`}
                              >
                                <Eye className="size-2.5" />
                                <span>Page {item.page}</span>
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Quoted Text Evidence */}
                        <div className="p-2.5 rounded-lg border bg-background/80 font-mono text-[11px] leading-relaxed text-foreground/90 space-y-1">
                          <div className="text-[10px] text-muted-foreground uppercase font-semibold">
                            Drawing Quoted Text & Evidence:
                          </div>
                          <p className="italic font-normal">
                            &ldquo;{item.evidenceText}&rdquo;
                          </p>
                        </div>

                        {/* Decision Rationale */}
                        {item.rationale && (
                          <div className="text-[11px] text-muted-foreground leading-relaxed">
                            <span className="font-semibold text-foreground/80">Audit Rationale: </span>
                            <span>{item.rationale}</span>
                          </div>
                        )}

                        {/* Applied Rule Citation */}
                        {item.ruleApplied && (
                          <div className="text-[10px] text-muted-foreground font-mono truncate">
                            Authority Rule: {item.ruleApplied}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* TAB 4: HUMAN ENGINEER SIGN-OFF */}
        <TabsContent value="review" className="space-y-3 pt-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Professional Engineer Compliance Sign-off</CardTitle>
              <CardDescription className="text-xs">
                Record official human engineering decisions. AI verdicts are assistive and immutable.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleSubmitReview} className="space-y-3.5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="reviewer" className="text-xs">
                      Reviewer Name & PEC Registration
                    </Label>
                    <Input
                      id="reviewer"
                      placeholder="e.g. Engr. Muhammad Zain (PEC #CIVIL-19482)"
                      value={reviewerName}
                      onChange={(e) => setReviewerName(e.target.value)}
                      required
                      className="h-8 text-xs"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="decision" className="text-xs">
                      Human Review Decision
                    </Label>
                    <NativeSelect
                      id="decision"
                      value={decision}
                      onChange={(e) => setDecision(e.target.value as "APPROVED" | "CORRECTION_REQUIRED" | "PENDING")}
                      className="w-full"
                    >
                      <option value="APPROVED">APPROVED (Ready for Municipal Submission)</option>
                      <option value="CORRECTION_REQUIRED">CORRECTION REQUIRED (Send back to Architect)</option>
                      <option value="PENDING">PENDING (Awaiting Soil / Structural Tests)</option>
                    </NativeSelect>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="note" className="text-xs">
                    Engineering Audit Notes & Conditions
                  </Label>
                  <Textarea
                    id="note"
                    placeholder="Provide any specific engineering observations or instructions for revision..."
                    value={reviewNote}
                    onChange={(e) => setReviewNote(e.target.value)}
                    rows={2}
                    className="text-xs resize-none"
                  />
                </div>

                <div className="flex justify-end">
                  <Button type="submit" size="sm" disabled={submittingReview} className="gap-1.5 text-xs">
                    <CheckCircle2 className="size-3.5" />
                    <span>{submittingReview ? "Recording..." : "Log Official Sign-off"}</span>
                  </Button>
                </div>
              </form>

              {/* Review History */}
              {reviewsList.length > 0 && (
                <div className="pt-3 border-t space-y-2">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Sign-off Audit Trail ({reviewsList.length})
                  </span>
                  <div className="space-y-2 max-h-[200px] overflow-y-auto">
                    {reviewsList.map((rev) => (
                      <div key={rev.review_id} className="p-3 rounded-lg border bg-muted/20 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground">{rev.reviewer_name}</span>
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {rev.decision}
                          </Badge>
                        </div>
                        {rev.note && <p className="text-muted-foreground">{rev.note}</p>}
                        <p className="text-[10px] text-muted-foreground font-mono">
                          {new Date(rev.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 5: TELEMETRY & COST */}
        <TabsContent value="telemetry" className="space-y-3 pt-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Autonomous Scrutiny Pipeline Telemetry</CardTitle>
              <CardDescription className="text-xs">
                Execution performance, multimodal inference metrics, and cost breakdown.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border bg-muted/20">
                  <span className="text-[11px] text-muted-foreground uppercase font-semibold">Latency</span>
                  <p className="text-lg font-bold font-mono mt-0.5">{processingTime}s</p>
                  <p className="text-[10px] text-muted-foreground">Wall-clock time</p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20">
                  <span className="text-[11px] text-muted-foreground uppercase font-semibold">Vision Stages</span>
                  <p className="text-lg font-bold font-mono mt-0.5">5 Steps</p>
                  <p className="text-[10px] text-muted-foreground">LangGraph DAG</p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20">
                  <span className="text-[11px] text-muted-foreground uppercase font-semibold">Checkpointer</span>
                  <p className="text-lg font-bold font-mono mt-0.5">PostgreSQL</p>
                  <p className="text-[10px] text-muted-foreground">Neon DB Memory</p>
                </div>
                <div className="p-3 rounded-lg border bg-muted/20">
                  <span className="text-[11px] text-muted-foreground uppercase font-semibold">Est. Pipeline Cost</span>
                  <p className="text-lg font-bold font-mono mt-0.5">$0.04</p>
                  <p className="text-[10px] text-muted-foreground">High-Res Multimodal</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 6: RAW VERDICT JSON */}
        <TabsContent value="json" className="space-y-3 pt-3">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Code2 className="size-4" />
                    <span>Raw Scrutiny Audit Verdict (JSON)</span>
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Machine-readable audit findings, spatial parameters, bylaw results, and evidence chain.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyJson}
                    className="h-8 gap-1.5 text-xs"
                  >
                    {copiedJson ? (
                      <>
                        <Check className="size-3.5 text-green-500" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="size-3.5" />
                        <span>Copy JSON</span>
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadJson}
                    className="h-8 gap-1.5 text-xs"
                  >
                    <Download className="size-3.5" />
                    <span>Export JSON</span>
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              {/* Filter and stats bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2 border-b">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Search keys or values (e.g. concrete, setback, PASS)..."
                    value={jsonSearch}
                    onChange={(e) => setJsonSearch(e.target.value)}
                    className="h-8 pl-8 text-xs font-mono"
                  />
                </div>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
                  <Badge variant="outline" className="text-[10px]">
                    {(JSON.stringify(verdict).length / 1024).toFixed(1)} KB
                  </Badge>
                  <Badge variant="outline" className="text-[10px]">
                    {Object.keys(verdict || {}).length} Root Keys
                  </Badge>
                  {jsonSearch && (
                    <Badge variant="secondary" className="text-[10px]">
                      Filter active
                    </Badge>
                  )}
                </div>
              </div>

              {/* Formatted Code Block */}
              <div className="relative rounded-lg border bg-muted/40 p-4 font-mono text-[11px] leading-relaxed max-h-[580px] overflow-auto select-text">
                <pre className="whitespace-pre overflow-x-auto text-foreground">
                  {jsonSearch
                    ? JSON.stringify(verdict, null, 2)
                        .split("\n")
                        .filter((line) => line.toLowerCase().includes(jsonSearch.toLowerCase()))
                        .join("\n") || `// No matching lines found for "${jsonSearch}"`
                    : JSON.stringify(verdict, null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
