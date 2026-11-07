import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { formatNumber, formatPercent, formatVnd } from "@/lib/format"
import { cn } from "@/lib/utils"

import type { Order, RankingRow } from "../types"

const GROUP = {
  buy: { label: "Mua", dot: "bg-success", text: "text-success" },
  sell: { label: "Bán", dot: "bg-destructive", text: "text-destructive" },
  hold: { label: "Giữ nguyên", dot: "bg-muted-foreground", text: "text-muted-foreground" },
} as const

type GroupProps = { action: Order["action"]; orders: Order[]; ranks: Map<string, RankingRow>; total: number; equity: number }

function Group({ action, orders, ranks, total, equity }: GroupProps) {
  if (!orders.length) return null
  const style = GROUP[action]
  const value = orders.reduce((sum, order) => sum + order.value, 0)
  return (
    <section>
      <div className="flex items-center gap-2 border-b pb-1.5 text-sm">
        <span className={cn("size-2 rounded-full", style.dot)} />
        <span className={cn("font-medium", style.text)}>{style.label}</span>
        <span className="text-muted-foreground">{orders.length} mã</span>
        <span className="ml-auto font-medium tabular-nums">{formatVnd(value)}</span>
      </div>
      <ul className="divide-y divide-border/50">
        {orders.map((order) => {
          const rank = ranks.get(order.symbol)
          return (
            <li key={order.symbol} className="grid grid-cols-[3.25rem_minmax(0,1fr)_auto] items-center gap-2 py-2">
              <span className="text-base font-semibold">{order.symbol}</span>
              <div className="text-xs text-muted-foreground tabular-nums">
                <div className="text-foreground/80">
                  {formatNumber(order.shares)} cp × {formatNumber(order.price)}
                </div>
                {rank && action !== "hold" && (
                  <div>
                    hạng {rank.rank}/{total} ·{" "}
                    <span className={rank.score < 0 ? "text-amber-500" : "text-success"}>
                      {rank.score >= 0 ? "+" : ""}
                      {formatNumber(rank.score, 3)}
                    </span>
                  </div>
                )}
              </div>
              <div className="text-right tabular-nums">
                <div className="text-sm">{formatVnd(order.value)}</div>
                <div className="text-xs text-muted-foreground">{formatPercent(order.value / equity, 1)}</div>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

type Props = { orders: Order[]; ranking: RankingRow[]; equity: number; className?: string }

export function OrdersCard({ orders, ranking, equity, className }: Props) {
  const ranks = new Map(ranking.map((row) => [row.symbol, row]))
  const by = (action: Order["action"]) => orders.filter((order) => order.action === action)
  const idle = orders.every((order) => order.action === "hold")
  return (
    <Card className={cn("min-h-0 gap-3 py-4", className)}>
      <CardHeader className="gap-0.5">
        <CardTitle>Lệnh phiên tới</CardTitle>
        <CardDescription>Khớp giá mở cửa, giá trị ước tính, % trên tổng vốn</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 space-y-4 overflow-y-auto">
        {idle && <p className="text-sm text-muted-foreground">Không có lệnh mua hoặc bán mới{orders.length === 0 ? ": chưa mã nào đạt điều kiện mua, vốn giữ tiền mặt" : ""}.</p>}
        {(["buy", "sell", "hold"] as const).map((action) => (
          <Group key={action} action={action} orders={by(action)} ranks={ranks} total={ranking.length} equity={equity} />
        ))}
      </CardContent>
    </Card>
  )
}
