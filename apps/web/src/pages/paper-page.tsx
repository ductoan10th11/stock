import { useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { useEffect } from "react"
import { useSearchParams } from "react-router-dom"

import { prefetchPaperPage } from "@/app/prefetch"
import { PageHeader } from "@/components/page-header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useMeta } from "@/features/meta/hooks"
import { AccountOverview } from "@/features/paper/components/account-view"
import { CreateAccountForm } from "@/features/paper/components/create-account-form"
import { ManageTab } from "@/features/paper/components/manage-tab"
import { Rules } from "@/features/paper/components/rules"
import { OverviewSkeleton, TableSkeleton } from "@/features/paper/components/skeletons"
import { TradesTable } from "@/features/paper/components/trades-table"
import { usePaperState, useRefreshPaper } from "@/features/paper/hooks"
import { PredictionsTab } from "@/features/predictions/components/predictions-tab"
import { formatDate } from "@/lib/format"
import { cn } from "@/lib/utils"

export function PaperPage() {
  const client = useQueryClient()
  const { data: meta } = useMeta()
  const { data: state, error } = usePaperState()
  const refresh = useRefreshPaper()
  const [params, setParams] = useSearchParams()
  useEffect(() => prefetchPaperPage(client), [client])

  const status = state?.data_ready
    ? `Nến ${formatDate(state.latest_candle!)} · tự cập nhật 15:30`
    : "Tiền ảo, giá thật"
  const ready = state === undefined || state.data_ready
  const trainedUntil = state?.trained_until ?? meta?.trained_until
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <PageHeader
        title="Paper Trading"
        description={status}
        action={
          <Button disabled={refresh.isPending} onClick={() => refresh.mutate()} title="Tải nến mới, chấm điểm 19 mã, chạy phiên mới cho tài khoản (cần mạng, vài chục giây)">
            <RefreshCw className={refresh.isPending ? "animate-spin" : undefined} />
            {refresh.isPending ? "Đang cập nhật..." : "Cập nhật dữ liệu"}
          </Button>
        }
      />
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}
      {state && !state.data_ready && (
        <Alert>
          <AlertDescription>Chưa có dữ liệu giá trực tiếp. Bấm Cập nhật dữ liệu để tải nến lần đầu (cần mạng).</AlertDescription>
        </Alert>
      )}
      {ready && (
        <Tabs
          className={cn("min-h-0 flex-1 transition-opacity", refresh.isPending && "pointer-events-none opacity-60")}
          aria-busy={refresh.isPending}
          value={params.get("tab") ?? "overview"}
          onValueChange={(tab) => setParams((current) => new URLSearchParams({ ...Object.fromEntries(current), tab }), { replace: true })}
        >
          <TabsList className="h-auto flex-wrap">
            <TabsTrigger value="overview">Tổng quan</TabsTrigger>
            <TabsTrigger value="predictions">Dự đoán</TabsTrigger>
            <TabsTrigger value="history">Lịch sử lệnh{state?.trades.length ? ` (${state.trades.length})` : ""}</TabsTrigger>
            <TabsTrigger value="settings">Cài đặt</TabsTrigger>
          </TabsList>
          <TabsContent value="overview" className="min-h-0">
            {!state || !meta ? (
              <OverviewSkeleton />
            ) : state.account ? (
              <AccountOverview meta={meta} state={state} />
            ) : (
              <div className="h-full md:overflow-y-auto">
                <CreateAccountForm meta={meta} state={state} />
              </div>
            )}
          </TabsContent>
          <TabsContent value="predictions" className="min-h-0">
            <PredictionsTab state={state} />
          </TabsContent>
          <TabsContent value="history" className="min-h-0 md:overflow-y-auto">
            {!state ? (
              <TableSkeleton />
            ) : (
              <Card>
                <CardContent>
                  {state.trades.length ? <TradesTable trades={state.trades} /> : <p className="py-6 text-center text-sm text-muted-foreground">Chưa có lệnh nào được khớp.</p>}
                </CardContent>
              </Card>
            )}
          </TabsContent>
          <TabsContent value="settings" className="min-h-0 space-y-3 md:overflow-y-auto">
            {trainedUntil && <Rules trainedUntil={trainedUntil} />}
            {state?.account && (
              <Card>
                <CardContent>
                  <ManageTab />
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
