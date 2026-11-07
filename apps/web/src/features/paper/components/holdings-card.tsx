import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatNumber, formatSignedPercent, formatVnd } from "@/lib/format"
import { cn } from "@/lib/utils"

import { CASH_COLOR, PALETTE } from "../palette"
import type { Position, Summary } from "../types"

type Props = { positions: Position[]; summary: Summary | null; initialCapital: number; className?: string }

export function HoldingsCard({ positions, summary, initialCapital, className }: Props) {
  const sorted = [...positions].sort((a, b) => b.value - a.value)
  const invested = sorted.reduce((total, position) => total + position.value, 0)
  const cash = summary?.cash ?? initialCapital
  const total = cash + invested
  const parts = [...sorted.map((position, index) => ({ key: position.symbol, value: position.value, color: PALETTE[index % PALETTE.length] })), { key: "cash", value: cash, color: CASH_COLOR }]
  return (
    <Card className={cn("min-h-0 gap-3 py-4", className)}>
      <CardHeader className="gap-0.5">
        <CardTitle>Đang giữ</CardTitle>
        <CardDescription>{sorted.length ? `${sorted.length} mã, tiền mặt ${formatVnd(cash)}` : "Chưa giữ mã nào, toàn bộ vốn là tiền mặt."}</CardDescription>
      </CardHeader>
      {sorted.length > 0 && (
        <CardContent className="min-h-0 space-y-3 overflow-y-auto">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-muted" role="img" aria-label="Phân bổ vốn">
            {parts.map((part) => (
              <div key={part.key} style={{ width: `${(part.value / total) * 100}%`, background: part.color }} />
            ))}
          </div>
          <ul className="divide-y">
            {sorted.map((position, index) => (
              <li key={position.symbol} className="flex items-center gap-3 py-2 text-sm">
                <span className="size-2.5 shrink-0 rounded-full" style={{ background: PALETTE[index % PALETTE.length] }} />
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{position.symbol}</div>
                  <div className="text-xs text-muted-foreground tabular-nums">
                    {formatNumber(position.shares)} cp · giữ {position.held} phiên
                  </div>
                </div>
                <div className="text-right tabular-nums">
                  <div>{formatVnd(position.value)}</div>
                  <div className={cn("text-xs", position.pnl_pct >= 0 ? "text-success" : "text-destructive")}>{formatSignedPercent(position.pnl_pct, 1)}</div>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      )}
    </Card>
  )
}
