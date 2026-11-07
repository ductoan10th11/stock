import { useSearchParams } from "react-router-dom"
import { useState } from "react"

import { PageHeader } from "@/components/page-header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ModelReview } from "@/features/backtest/components/model-review"
import { Notes } from "@/features/backtest/components/notes"
import { Results } from "@/features/backtest/components/results"
import { ResultsSkeleton } from "@/features/backtest/components/skeletons"
import { Toolbar } from "@/features/backtest/components/toolbar"
import { formProblem, initialForm, toRequest } from "@/features/backtest/form"
import { useBacktest } from "@/features/backtest/hooks"
import { useMeta } from "@/features/meta/hooks"
import type { Meta } from "@/features/meta/types"
import { useDebouncedValue } from "@/hooks/use-debounced-value"
import { formatDate } from "@/lib/format"

const SIMULATION_TABS = ["growth", "table", "detail"]

function Workspace({ meta }: { meta: Meta }) {
  const [form, setForm] = useState(() => initialForm(meta))
  const [params, setParams] = useSearchParams()
  const tab = params.get("tab") ?? "growth"
  const debounced = useDebouncedValue(form, 300)
  const problem = formProblem(debounced)
  const request = problem ? null : toRequest(debounced)
  const query = useBacktest(request)
  const data = query.data
  const summary = data ? `${formatDate(data.start)} đến ${formatDate(data.end)} · ${data.sessions} phiên` : undefined
  return (
    <Tabs
      className="min-h-0 flex-1"
      value={tab}
      onValueChange={(next) => setParams((current) => new URLSearchParams({ ...Object.fromEntries(current), tab: next }), { replace: true })}
    >
      <TabsList>
        <TabsTrigger value="growth">Tăng trưởng</TabsTrigger>
        <TabsTrigger value="table">Bảng so sánh</TabsTrigger>
        <TabsTrigger value="detail">Theo năm và phí</TabsTrigger>
        <TabsTrigger value="predictions">Dự đoán mô hình</TabsTrigger>
        <TabsTrigger value="notes">Giả định</TabsTrigger>
      </TabsList>
      {SIMULATION_TABS.includes(tab) && (
        <>
          <Toolbar meta={meta} form={form} onChange={setForm} busy={form !== debounced} summary={summary} />
          {problem && (
            <Alert>
              <AlertDescription>{problem === "no_strategy" ? "Chọn ít nhất một chiến thuật." : "Tổ hợp cần ít nhất một trọng số khác 0 (Nâng cao)."}</AlertDescription>
            </Alert>
          )}
          <Results request={request} query={query} />
        </>
      )}
      <TabsContent value="predictions" className="min-h-0">
        <ModelReview />
      </TabsContent>
      <TabsContent value="notes" className="min-h-0 md:overflow-y-auto">
        <Card>
          <CardContent>
            <Notes meta={meta} />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}

export function BacktestPage() {
  const { data: meta } = useMeta()
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <PageHeader title="Backtest" description="19 mã, đã tính phí, trượt giá và giới hạn khớp lệnh" />
      {!meta && (
        <>
          <Skeleton className="h-[3.25rem] w-full shrink-0 rounded-xl" />
          <ResultsSkeleton />
        </>
      )}
      {meta && !meta.backtest_ready && (
        <Alert variant="destructive">
          <AlertDescription>
            Thiếu results/research/pooled_abs_full/oof.csv.gz. Chạy scripts/panel_data.py rồi scripts/panel_experiments.py --name pooled_abs_full --mode pooled --label abs --features full.
          </AlertDescription>
        </Alert>
      )}
      {meta?.backtest_ready && <Workspace meta={meta} />}
    </div>
  )
}
