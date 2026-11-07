import { CircleCheck } from "lucide-react"

import { HelpTip } from "@/components/help-tip"
import { Card, CardContent } from "@/components/ui/card"
import { formatNumber, formatPercent } from "@/lib/format"

import type { Curve, MetricsRow } from "../types"

type Props = { rows: MetricsRow[]; equalWeight: MetricsRow; curves: Curve[] }

const VERDICT = {
  significant: { text: "Có ý nghĩa thống kê", className: "text-success" },
  insufficient: { text: "Chưa đủ bằng chứng", className: "text-amber-500" },
  unknown: { text: "Chưa đánh giá được", className: "text-muted-foreground" },
} as const

export function StrategyCards({ rows, equalWeight, curves }: Props) {
  const color = (key: string) => curves.find((curve) => curve.key === key)?.color
  return (
    <div className="grid shrink-0 grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-3">
      {rows.map((row) => {
        const delta = ((row.return_ann ?? 0) - (equalWeight.return_ann ?? 0)) * 100
        const verdict = VERDICT[row.verdict ?? "unknown"]
        return (
          <Card key={row.key} className="gap-0 py-3">
            <CardContent className="space-y-0.5">
              <div className="flex items-center gap-2 text-sm">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: color(row.key) }} />
                <span className="truncate font-medium">{row.label}</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-medium tabular-nums">{formatPercent(row.return_ann)}</span>
                <span className="text-xs text-muted-foreground">/ năm</span>
                <span className={`ml-auto text-xs tabular-nums ${delta >= 0 ? "text-success" : "text-destructive"}`}>
                  {delta >= 0 ? "▲" : "▼"} {formatNumber(Math.abs(delta), 1)} điểm
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground tabular-nums">
                Sharpe {formatNumber(row.sharpe, 2)} · Sụt giảm {formatPercent(row.max_drawdown, 0)} ·
                <span className={`inline-flex items-center gap-1 ${verdict.className}`}>
                  {row.verdict === "significant" && <CircleCheck className="size-3" />}
                  {verdict.text}
                </span>
                <HelpTip>Điểm = chênh lệch lợi suất năm so với cân bằng đều 19 mã. Ý nghĩa thống kê: khoảng tin cậy 95% của alpha (đã hiệu chỉnh cho số chiến thuật thử) nằm hẳn trên 0.</HelpTip>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
