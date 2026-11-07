import { Download } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatNumber, formatSignedPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

import type { Trade } from "../types"

const COLUMNS = ["date", "symbol", "side", "shares", "price", "value", "fee", "entry_price", "entry_value", "pnl", "pnl_pct"] as const

function downloadCsv(trades: Trade[]) {
  const lines = [COLUMNS.join(","), ...trades.map((trade) => COLUMNS.map((column) => trade[column] ?? "").join(","))]
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }))
  const link = Object.assign(document.createElement("a"), { href: url, download: "paper_trades.csv" })
  link.click()
  URL.revokeObjectURL(url)
}

function PriceCell({ price, value }: { price: number; value: number }) {
  return (
    <>
      <div>{formatNumber(price)}</div>
      <div className="text-xs text-muted-foreground">{formatNumber(value)}</div>
    </>
  )
}

type Filter = "all" | Trade["side"]

export function TradesTable({ trades: all }: { trades: Trade[] }) {
  const [filter, setFilter] = useState<Filter>("all")
  const count = (side: Trade["side"]) => all.filter((trade) => trade.side === side).length
  const trades = filter === "all" ? all : all.filter((trade) => trade.side === filter)
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Tabs value={filter} onValueChange={(value) => setFilter(value as Filter)}>
          <TabsList>
            <TabsTrigger value="all">Tất cả ({all.length})</TabsTrigger>
            <TabsTrigger value="buy">Mua ({count("buy")})</TabsTrigger>
            <TabsTrigger value="sell">Bán ({count("sell")})</TabsTrigger>
          </TabsList>
        </Tabs>
        <Button variant="outline" size="sm" onClick={() => downloadCsv(trades)}>
          <Download />
          Tải CSV
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Ngày</TableHead>
            <TableHead>Mã</TableHead>
            <TableHead>Lệnh</TableHead>
            <TableHead className="text-right">Số CP</TableHead>
            <TableHead className="text-right">Giá khớp / Giá trị (đ)</TableHead>
            <TableHead className="text-right">Giá vào / Giá trị vào (đ)</TableHead>
            <TableHead className="text-right">Phí (đ)</TableHead>
            <TableHead className="text-right">Lãi/lỗ (đ)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade, index) => (
            <TableRow key={`${trade.date}-${trade.symbol}-${index}`}>
              <TableCell>{trade.date}</TableCell>
              <TableCell className="font-medium">{trade.symbol}</TableCell>
              <TableCell>
                <Badge variant={trade.side === "buy" ? "default" : "destructive"}>{trade.side === "buy" ? "Mua" : "Bán"}</Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatNumber(trade.shares)}</TableCell>
              <TableCell className="text-right tabular-nums">
                <PriceCell price={trade.price} value={trade.value} />
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {trade.entry_price == null || trade.entry_value == null ? "-" : <PriceCell price={trade.entry_price} value={trade.entry_value} />}
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatNumber(trade.fee)}</TableCell>
              <TableCell className={cn("text-right tabular-nums", trade.pnl != null && (trade.pnl >= 0 ? "text-success" : "text-destructive"))}>
                {trade.pnl == null || trade.pnl_pct == null ? "-" : `${trade.pnl >= 0 ? "+" : ""}${formatNumber(trade.pnl)} (${formatSignedPercent(trade.pnl_pct, 1)})`}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
