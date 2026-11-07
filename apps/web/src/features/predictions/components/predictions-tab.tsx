import { useSearchParams } from "react-router-dom"

import { HelpTip } from "@/components/help-tip"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { PaperState } from "@/features/paper/types"
import { formatDate } from "@/lib/format"

import { useLatestPredictions, usePrefetchSymbol, useSymbolPredictions } from "../hooks"
import { CandleChart } from "./candle-chart"
import { Marker } from "./marker"
import { NextSessionCard } from "./next-session-card"
import { planOf } from "./plan"
import { ListSkeleton, PanelSkeleton } from "./skeletons"
import { SymbolList } from "./symbol-list"

function LegendMarker({ direction, correct, label }: { direction: "up" | "down" | "flat"; correct: boolean | null; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <svg width={12} height={12} aria-hidden>
        <Marker cx={6} cy={6} direction={direction} correct={correct} />
      </svg>
      {label}
    </span>
  )
}

export function Legend({ learned = true }: { learned?: boolean }) {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
      <span>Mũi tên dưới nến = dự đoán phiên sau:</span>
      <LegendMarker direction="up" correct label="tăng" />
      <LegendMarker direction="down" correct label="giảm" />
      <LegendMarker direction="flat" correct label="ngang" />
      <LegendMarker direction="up" correct label="đặc: đúng" />
      <LegendMarker direction="up" correct={false} label="rỗng: sai" />
      {learned && (
        <span className="inline-flex items-center gap-1">
          <span className="size-2.5 rounded-sm bg-foreground/15" />
          xám: mô hình đã học giai đoạn này, không có dự đoán ngoài mẫu
        </span>
      )}
    </div>
  )
}

export function PredictionsTab({ state }: { state: PaperState | undefined }) {
  const [params, setParams] = useSearchParams()
  const latest = useLatestPredictions()
  const symbol = params.get("symbol") ?? latest.data?.rows[0]?.symbol
  const detail = useSymbolPredictions(symbol)
  const prefetch = usePrefetchSymbol()
  const plan = planOf(state)
  const row = latest.data?.rows.find((item) => item.symbol === symbol)
  const select = (next: string) =>
    setParams((current) => new URLSearchParams({ ...Object.fromEntries(current), symbol: next }), { replace: true })

  if (latest.error)
    return (
      <Alert variant="destructive">
        <AlertDescription>Không tải được dự đoán.</AlertDescription>
      </Alert>
    )
  return (
    <div className="flex flex-col gap-3 lg:h-full">
      {latest.data?.in_sample && (
        <Alert>
          <AlertDescription>
            Dự đoán mới nhất ({formatDate(latest.data.date)}) nằm trong giai đoạn mô hình đã học (đến {formatDate(latest.data.trained_until)}), nên chưa phản ánh khả năng dự đoán thật.
          </AlertDescription>
        </Alert>
      )}
      <div className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[17.5rem_minmax(0,1fr)]">
        <Card className="order-2 min-h-0 gap-0 overflow-hidden py-0 lg:order-1">
          <CardHeader className="flex shrink-0 flex-row items-baseline justify-between gap-2 border-b py-3">
            <CardTitle>Dự đoán</CardTitle>
            <span className="text-xs text-muted-foreground">{latest.data ? `phiên tới · ${formatDate(latest.data.date)}` : "..."}</span>
          </CardHeader>
          <ScrollArea className="min-h-0 flex-1">
            {latest.data ? <SymbolList rows={latest.data.rows} selected={symbol} onSelect={select} onHover={prefetch} plan={plan} /> : <ListSkeleton />}
          </ScrollArea>
        </Card>
        <div className="order-1 flex min-h-0 min-w-0 flex-col gap-3 lg:order-2">
          {detail.data && latest.data ? (
            <>
              <NextSessionCard data={detail.data} row={row} plan={plan[detail.data.symbol]} total={latest.data.rows.length} />
              <Card className="min-h-0 gap-2 py-3 lg:flex-1">
                <CardHeader className="shrink-0">
                  <CardTitle className="flex items-center gap-1.5">
                    {detail.data.symbol}: nến ngày và xu hướng dự đoán
                    <HelpTip>90 phiên gần nhất, giá tính bằng nghìn đồng. Nến xanh là giá đóng cửa cao hơn mở cửa, nến đỏ là thấp hơn. Khi rê chuột vào một ngày sẽ thấy giá và dự đoán của ngày đó.</HelpTip>
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex min-h-0 flex-1 flex-col gap-2">
                  <div className="min-h-0 flex-1">
                    <CandleChart data={detail.data} />
                  </div>
                  <Legend />
                </CardContent>
              </Card>
            </>
          ) : detail.error ? (
            <Alert variant="destructive">
              <AlertDescription>Không tải được dự đoán của {symbol}.</AlertDescription>
            </Alert>
          ) : (
            <PanelSkeleton symbol={symbol} />
          )}
        </div>
      </div>
    </div>
  )
}
