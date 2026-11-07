import { useQueryClient } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"

import { DatePicker } from "@/components/date-picker"
import { HelpTip } from "@/components/help-tip"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { CandleChart } from "@/features/predictions/components/candle-chart"
import { Legend } from "@/features/predictions/components/predictions-tab"
import { formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

import { reviewSymbolQuery, useReviewList, useReviewSymbol } from "../hooks"
import type { ReviewWindow } from "../types"

const SPANS = [
  { id: "week", label: "7 ngày" },
  { id: "month", label: "1 tháng" },
  { id: "year", label: "1 năm" },
] as const

const DEFAULT_SYMBOL = "TCB"
const DAY_MS = 864e5
const shiftDate = (iso: string, days: number) => new Date(Date.parse(iso) + days * DAY_MS).toISOString().slice(0, 10)

const toneOf = (rate: number) => (rate >= 0.36 ? "text-success" : rate < 0.33 ? "text-destructive" : "")

function ListSkeleton() {
  return (
    <div className="space-y-2 px-3 py-2" aria-busy="true">
      {Array.from({ length: 19 }, (_, index) => (
        <Skeleton key={index} className="h-6 w-full" />
      ))}
    </div>
  )
}

function ChartSkeleton({ symbol }: { symbol: string | undefined }) {
  return (
    <Card className="min-h-0 gap-2 py-3 lg:flex-1" aria-busy="true" aria-label={`Đang tải ${symbol ?? ""}`}>
      <CardHeader className="shrink-0">
        <CardTitle>{symbol ?? "Đang tải..."}</CardTitle>
      </CardHeader>
      <CardContent className="flex min-h-0 flex-1 flex-col gap-2">
        <Skeleton className="h-[340px] w-full lg:h-auto lg:min-h-0 lg:flex-[3]" />
        <Skeleton className="h-[110px] w-full lg:h-auto lg:min-h-[70px] lg:flex-1" />
      </CardContent>
    </Card>
  )
}

export function ModelReview() {
  const client = useQueryClient()
  const [window, setWindow] = useState<ReviewWindow>({ span: "month" })
  const [picked, setPicked] = useState<string>()
  const list = useReviewList(window)
  const range = list.data
  const symbol = picked ?? (range?.rows.some((row) => row.symbol === DEFAULT_SYMBOL) ? DEFAULT_SYMBOL : range?.rows[0]?.symbol)
  const detail = useReviewSymbol(symbol, window)

  const setDates = (start: string, end: string) => {
    if (!range || start > end) return
    setWindow({ start: start < range.first_date ? range.first_date : start, end: end > range.last_date ? range.last_date : end })
  }
  const shift = (direction: -1 | 1) => {
    if (!range) return
    const days = Math.round((Date.parse(range.end) - Date.parse(range.start)) / DAY_MS) + 1
    const start = shiftDate(range.start, direction * days)
    const end = shiftDate(range.end, direction * days)
    if (direction < 0 ? range.start <= range.first_date : range.end >= range.last_date) return
    setDates(start, end)
  }
  const hit = detail.data?.hit_rate

  return (
    <div className="flex flex-col gap-3 lg:h-full">
      <Card className="shrink-0 gap-0 py-2">
        <CardContent className="flex flex-wrap items-center gap-2 px-3">
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={window.span ?? ""}
            onValueChange={(span) => span && setWindow({ span: span as ReviewWindow["span"] })}
            aria-label="Khoảng thời gian"
          >
            {SPANS.map((span) => (
              <ToggleGroupItem key={span.id} value={span.id}>
                {span.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <div className="flex items-center gap-1.5">
            <Button size="icon" variant="outline" className="size-8" aria-label="Lùi một khoảng" disabled={!range || range.start <= range.first_date} onClick={() => shift(-1)}>
              <ChevronLeft />
            </Button>
            <DatePicker label="Từ ngày" value={range?.start} min={range?.first_date} max={range?.end} onChange={(start) => setDates(start, range!.end)} />
            <span className="text-sm text-muted-foreground">đến</span>
            <DatePicker label="Đến ngày" value={range?.end} min={range?.start} max={range?.last_date} onChange={(end) => setDates(range!.start, end)} />
            <Button size="icon" variant="outline" className="size-8" aria-label="Tiến một khoảng" disabled={!range || range.end >= range.last_date} onClick={() => shift(1)}>
              <ChevronRight />
            </Button>
          </div>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-muted-foreground">
            Dự đoán ngoài mẫu của walk-forward
            <HelpTip>Mô hình ensemble3 gộp 19 mã, huấn luyện lại mỗi fold, chỉ chấm các phiên chưa từng học. Đoán đúng là hướng dự đoán (tăng, ngang, giảm) trùng hướng phiên sau. Ngẫu nhiên khoảng 33 đến 36%; một mã trong vài ngày thì dao động rất mạnh.</HelpTip>
          </span>
        </CardContent>
      </Card>
      {list.error && (
        <Alert variant="destructive">
          <AlertDescription>Không tải được dự đoán của mô hình.</AlertDescription>
        </Alert>
      )}
      <div className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <Card className="order-2 min-h-0 gap-0 overflow-hidden py-0 lg:order-1">
          <CardHeader className="flex shrink-0 flex-row items-baseline justify-between gap-2 border-b py-3">
            <CardTitle>Theo mã</CardTitle>
            {range && range.total > 0 && (
              <span className={cn("text-xs tabular-nums", toneOf(range.correct / range.total))}>
                tất cả {formatPercent(range.correct / range.total, 0)}
              </span>
            )}
          </CardHeader>
          <ScrollArea className="min-h-0 flex-1">
            {range ? (
              <Table>
                <TableBody>
                  {range.rows.map((row) => (
                    <TableRow
                      key={row.symbol}
                      role="button"
                      tabIndex={0}
                      data-state={row.symbol === symbol ? "selected" : undefined}
                      className="cursor-pointer"
                      onClick={() => setPicked(row.symbol)}
                      onKeyDown={(event) => event.key === "Enter" && setPicked(row.symbol)}
                      onPointerEnter={() => void client.prefetchQuery(reviewSymbolQuery(row.symbol, window))}
                    >
                      <TableCell className="py-1.5 pl-3 font-medium">{row.symbol}</TableCell>
                      <TableCell className="py-1.5 text-right text-xs text-muted-foreground tabular-nums">
                        {row.correct}/{row.total}
                      </TableCell>
                      <TableCell className={cn("py-1.5 pr-3 text-right text-xs tabular-nums", row.total ? toneOf(row.correct / row.total) : "text-muted-foreground")}>
                        {row.total ? formatPercent(row.correct / row.total, 0) : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <ListSkeleton />
            )}
          </ScrollArea>
        </Card>
        <div className="order-1 flex min-h-0 min-w-0 flex-col gap-3 lg:order-2">
          {detail.data && detail.data.candles.length > 0 ? (
            <Card className="min-h-0 gap-2 py-3 lg:flex-1">
              <CardHeader className="flex shrink-0 flex-row items-center gap-2">
                <CardTitle>{detail.data.symbol}</CardTitle>
                {hit && (
                  <span className={cn("text-sm tabular-nums", toneOf(hit.correct / hit.total))}>
                    đoán đúng {hit.correct}/{hit.total} phiên ({formatPercent(hit.correct / hit.total, 0)})
                  </span>
                )}
                <span className="ml-auto text-xs text-muted-foreground">giá nghìn đồng</span>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col gap-2">
                <div className="min-h-0 flex-1">
                  <CandleChart data={detail.data} />
                </div>
                <Legend learned={false} />
              </CardContent>
            </Card>
          ) : detail.error ? (
            <Alert variant="destructive">
              <AlertDescription>Không tải được dự đoán của {symbol}.</AlertDescription>
            </Alert>
          ) : detail.data ? (
            <p className="py-10 text-center text-sm text-muted-foreground">Không có nến trong khoảng này.</p>
          ) : (
            <ChartSkeleton symbol={symbol} />
          )}
        </div>
      </div>
    </div>
  )
}
