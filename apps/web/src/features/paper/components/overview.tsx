import { TrendingDown, TrendingUp } from "lucide-react"
import type { ReactNode } from "react"

import { TimeLineChart, type LineSeries } from "@/components/line-chart"
import { HelpTip } from "@/components/help-tip"
import { Card, CardContent } from "@/components/ui/card"
import { ACCOUNT_COLOR, EQUAL_WEIGHT_COLOR, VNINDEX_COLOR } from "@/lib/colors"
import { formatDate, formatMultiple, formatPercent, formatSignedPercent, formatVnd } from "@/lib/format"
import { cn } from "@/lib/utils"

import { CASH_COLOR, PALETTE } from "../palette"
import type { AccountInfo, EquityCurve, Order, Summary } from "../types"

function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: "up" | "down" }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("text-base font-medium tabular-nums", tone === "up" && "text-success", tone === "down" && "text-destructive")}>{value}</dd>
    </div>
  )
}

const tone = (value: number | null) => (value == null ? undefined : value >= 0 ? "up" : "down")

function seriesOf(equity: EquityCurve): LineSeries[] {
  return [
    { key: "account", label: "Tài khoản", color: ACCOUNT_COLOR, dash: "solid", values: equity.account },
    { key: "equal_weight", label: "Cân bằng đều 19 mã", color: EQUAL_WEIGHT_COLOR, dash: "dash", values: equity.equal_weight },
    ...(equity.vnindex ? [{ key: "vnindex", label: "VN-Index", color: VNINDEX_COLOR, dash: "dot" as const, values: equity.vnindex }] : []),
  ]
}

function Title({ strategy, initialCapital }: { strategy: string; initialCapital: number }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm text-muted-foreground">
      <span className="flex items-center gap-1.5">
        Giá trị tài khoản
        <HelpTip>{strategy}</HelpTip>
      </span>
      <span>Vốn {formatVnd(initialCapital)}</span>
    </div>
  )
}

function PlannedAllocation({ orders, capital }: { orders: Order[]; capital: number }) {
  const buys = orders.filter((order) => order.action === "buy")
  const invested = buys.reduce((total, order) => total + order.value, 0)
  const rows = [...buys.map((order, index) => ({ key: order.symbol, value: order.value, color: PALETTE[index % PALETTE.length] })), { key: "Tiền mặt", value: Math.max(capital - invested, 0), color: CASH_COLOR }]
  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="text-sm font-medium">Phân bổ vốn dự kiến cho phiên đầu tiên</div>
      <div className="flex h-3 overflow-hidden rounded-full bg-muted">
        {rows.map((row) => (
          <div key={row.key} style={{ width: `${(row.value / capital) * 100}%`, background: row.color }} />
        ))}
      </div>
      <ul className="space-y-1.5 text-sm">
        {rows.map((row) => (
          <li key={row.key} className="flex items-center gap-2">
            <span className="size-2.5 rounded-full" style={{ background: row.color }} />
            <span className="w-20 font-medium">{row.key}</span>
            <span className="text-muted-foreground tabular-nums">{formatPercent(row.value / capital, 1)}</span>
            <span className="ml-auto tabular-nums">{formatVnd(row.value)}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">Biểu đồ giá trị tài khoản sẽ xuất hiện sau phiên giao dịch đầu tiên.</p>
    </div>
  )
}

type Props = { account: AccountInfo; strategy: string; summary: Summary | null; equity: EquityCurve | null; orders: Order[] }

export function Overview({ account, strategy, summary, equity, orders }: Props) {
  if (!summary || !equity) {
    return (
      <Card className="min-h-0 gap-3 py-4">
        <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
          <Title strategy={strategy} initialCapital={account.initial_capital} />
          <div>
            <div className="text-4xl font-medium tabular-nums">{formatVnd(account.initial_capital)}</div>
            <p className="text-sm text-muted-foreground">Tài khoản mở ngày {formatDate(account.start_date)}, chưa có phiên nào được xử lý. Lệnh khớp ở giá mở cửa phiên tới.</p>
          </div>
          <PlannedAllocation orders={orders} capital={account.initial_capital} />
        </CardContent>
      </Card>
    )
  }
  const up = summary.gain >= 0
  const values = [...equity.account, ...equity.equal_weight]
  const digits = Math.max(...values) - Math.min(...values) < 0.1 ? 3 : 2
  const Arrow = up ? TrendingUp : TrendingDown
  return (
    <Card className="min-h-0 gap-3 py-4">
      <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
        <Title strategy={strategy} initialCapital={account.initial_capital} />
        <div className="flex flex-wrap items-end justify-between gap-x-10 gap-y-3">
          <div>
            <div className="text-3xl font-medium tabular-nums">{formatVnd(summary.equity)}</div>
            <div className={cn("mt-1 flex items-center gap-1.5 text-sm tabular-nums", up ? "text-success" : "text-destructive")}>
              <Arrow className="size-4" />
              {formatSignedPercent(summary.gain_pct)} · {up ? "+" : "-"}
              {formatVnd(Math.abs(summary.gain))} từ {formatDate(account.start_date)}
            </div>
          </div>
          <dl className="flex flex-wrap gap-x-8 gap-y-3">
            <Stat label="Tiền mặt" value={formatPercent(summary.cash_pct, 0)} />
            <Stat label="Cân bằng đều 19 mã" value={summary.equal_weight_return == null ? "-" : formatSignedPercent(summary.equal_weight_return)} tone={tone(summary.equal_weight_return)} />
            <Stat label="VN-Index" value={summary.vnindex_return == null ? "-" : formatSignedPercent(summary.vnindex_return)} tone={tone(summary.vnindex_return)} />
          </dl>
        </div>
        <div className="h-[280px] min-h-0 lg:h-auto lg:flex-1">
          <TimeLineChart dates={equity.dates} series={seriesOf(equity)} formatValue={(value) => formatMultiple(value, digits)} fill area />
        </div>
      </CardContent>
    </Card>
  )
}
