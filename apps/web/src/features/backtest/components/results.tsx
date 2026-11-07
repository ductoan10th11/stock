import type { UseQueryResult } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useState } from "react"

import { HelpTip } from "@/components/help-tip"
import { TimeLineChart, type LineSeries } from "@/components/line-chart"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { TabsContent } from "@/components/ui/tabs"
import { ApiError } from "@/lib/api-client"
import { formatMultiple, formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

import { useRandomBaseline } from "../hooks"
import type { BacktestRequest, BacktestResponse } from "../types"
import { PercentGrid } from "./grid-table"
import { FULL_COLUMNS, MetricsTable, SUMMARY_COLUMNS } from "./metrics-table"
import { ResultsSkeleton } from "./skeletons"
import { StrategyCards } from "./strategy-cards"

const RANDOM_LABEL = "Chọn mã ngẫu nhiên"

function ErrorAlert({ error }: { error: Error }) {
  const missingOof = error instanceof ApiError && error.detail === "oof_missing"
  return (
    <Alert variant="destructive">
      <AlertTitle>{missingOof ? "Thiếu dữ liệu dự đoán của mô hình" : "Không chạy được backtest"}</AlertTitle>
      <AlertDescription>
        {missingOof
          ? "Thiếu results/research/pooled_abs_full/oof.csv.gz. Chạy scripts/panel_data.py rồi scripts/panel_experiments.py --name pooled_abs_full --mode pooled --label abs --features full."
          : error.message}
      </AlertDescription>
    </Alert>
  )
}

function ChartCard({ title, help, action, children }: { title: string; help: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="min-h-0 gap-2 py-3 lg:flex-1">
      <CardHeader className="flex shrink-0 flex-row items-center gap-1.5">
        <CardTitle>{title}</CardTitle>
        <HelpTip>{help}</HelpTip>
        {action && <div className="ml-auto flex items-center gap-2">{action}</div>}
      </CardHeader>
      <CardContent className="min-h-[220px] flex-1 lg:min-h-0">{children}</CardContent>
    </Card>
  )
}

function Loaded({ data, request, settled }: { data: BacktestResponse; request: BacktestRequest; settled: boolean }) {
  const [log, setLog] = useState(true)
  const [full, setFull] = useState(false)
  const random = useRandomBaseline(request, settled)
  const metrics = random.data ? [...data.metrics, random.data] : data.metrics
  const strategyRows = data.metrics.filter((row) => row.kind === "strategy")
  const equalWeight = data.metrics.find((row) => row.key === "equal_weight")!
  const asSeries = (field: "wealth" | "drawdown"): LineSeries[] =>
    data.curves.map((curve) => ({ key: curve.key, label: curve.label, color: curve.color, dash: curve.dash, values: curve[field] }))
  return (
    <>
      <TabsContent value="growth" className="flex min-h-0 flex-col gap-3">
        <StrategyCards rows={strategyRows} equalWeight={equalWeight} curves={data.curves} />
        <div className="flex min-h-0 flex-col gap-3 lg:flex-1">
          <ChartCard
            title="Giá trị tài khoản"
            help="1,0× là số vốn ban đầu; 2,0× là đã nhân đôi."
            action={
              <>
                <Switch id="log-scale" size="sm" checked={log} onCheckedChange={setLog} />
                <Label htmlFor="log-scale" className="text-xs font-normal">
                  Thang log
                </Label>
              </>
            }
          >
            <TimeLineChart dates={data.dates} series={asSeries("wealth")} formatValue={formatMultiple} log={log} fill />
          </ChartCard>
          <ChartCard title="Sụt giảm so với đỉnh" help="Mức tài khoản đang thấp hơn đỉnh gần nhất bao nhiêu; càng sâu càng khó chịu đựng.">
            <TimeLineChart dates={data.dates} series={asSeries("drawdown")} formatValue={(value) => formatPercent(value, 0)} fill />
          </ChartCard>
        </div>
      </TabsContent>
      <TabsContent value="table" className="min-h-0 md:overflow-y-auto">
        <Card className="gap-3 py-4">
          <CardHeader className="flex flex-row items-center gap-1.5">
            <CardTitle>Kết quả</CardTitle>
            <HelpTip>
              Ba dòng cuối là mốc so sánh: cân bằng đều, VN-Index mua và giữ, chọn mã ngẫu nhiên. Alpha là phần lợi suất vượt cân bằng đều 19 mã; CI là khoảng tin cậy 95%, "đa kiểm định" nới khoảng ra vì đã thử nhiều chiến thuật. Alpha chỉ đáng tin khi
              khoảng không chứa 0.
            </HelpTip>
            <div className="ml-auto flex items-center gap-2">
              <Switch id="full-columns" size="sm" checked={full} onCheckedChange={setFull} />
              <Label htmlFor="full-columns" className="text-xs font-normal">
                Đủ chỉ số
              </Label>
            </div>
          </CardHeader>
          <CardContent>
            <MetricsTable rows={metrics} columns={full ? FULL_COLUMNS : SUMMARY_COLUMNS} pendingLabel={random.data ? undefined : RANDOM_LABEL} />
          </CardContent>
        </Card>
      </TabsContent>
      <TabsContent value="detail" className="grid min-h-0 content-start gap-3 md:overflow-y-auto">
        <Card className="gap-3 py-4">
          <CardHeader>
            <CardTitle>Lợi suất theo năm</CardTitle>
          </CardHeader>
          <CardContent>
            <PercentGrid table={data.yearly} />
          </CardContent>
        </Card>
        <Card className="gap-3 py-4">
          <CardHeader className="flex flex-row items-center gap-1.5">
            <CardTitle>Alpha ròng khi phí thay đổi</CardTitle>
            <HelpTip>Phí tăng thì alpha giảm bao nhiêu; chiến thuật giao dịch nhiều sẽ nhạy hơn.</HelpTip>
          </CardHeader>
          <CardContent>
            <PercentGrid table={data.fee_sensitivity} />
          </CardContent>
        </Card>
      </TabsContent>
    </>
  )
}

export function Results({ request, query }: { request: BacktestRequest | null; query: UseQueryResult<BacktestResponse> }) {
  const { data, error, isFetching } = query
  if (!request) return null
  if (error) return <ErrorAlert error={error} />
  if (!data) return <ResultsSkeleton />
  return (
    <div className={cn("relative flex min-h-0 flex-1 flex-col transition-opacity", isFetching && "opacity-60")} aria-busy={isFetching}>
      {isFetching && <Loader2 className="absolute top-1 right-2 z-10 size-4 animate-spin text-muted-foreground" />}
      <Loaded data={data} request={request} settled={!isFetching} />
    </div>
  )
}
