import { ArrowDown, ArrowUp, Minus } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { DOWN_COLOR, FLAT_COLOR, UP_COLOR } from "@/lib/colors"
import { formatNumber } from "@/lib/format"
import { cn } from "@/lib/utils"

import { DIRECTION_LABEL, type PredictionRow } from "../types"
import { PLAN_LABEL, type Plan } from "./plan"

const ICON = { up: [ArrowUp, UP_COLOR], down: [ArrowDown, DOWN_COLOR], flat: [Minus, FLAT_COLOR] } as const

type Props = {
  rows: PredictionRow[]
  selected: string | undefined
  onSelect: (symbol: string) => void
  onHover: (symbol: string) => void
  plan: Record<string, Plan>
}

export function SymbolList({ rows, selected, onSelect, onHover, plan }: Props) {
  return (
    <Table>
      <TableBody>
        {rows.map((row) => {
          const [Icon, color] = ICON[row.direction]
          const action = plan[row.symbol]
          return (
            <TableRow
              key={row.symbol}
              role="button"
              tabIndex={0}
              data-state={row.symbol === selected ? "selected" : undefined}
              className="cursor-pointer"
              onClick={() => onSelect(row.symbol)}
              onKeyDown={(event) => event.key === "Enter" && onSelect(row.symbol)}
              onPointerEnter={() => onHover(row.symbol)}
              onFocus={() => onHover(row.symbol)}
            >
              <TableCell className="w-6 py-1.5 pr-0 pl-3 text-xs text-muted-foreground tabular-nums">{row.rank}</TableCell>
              <TableCell className="py-1.5 font-medium">{row.symbol}</TableCell>
              <TableCell className="py-1.5 text-xs" style={{ color }}>
                <span className="flex items-center gap-1">
                  <Icon className="size-3.5" />
                  {DIRECTION_LABEL[row.direction]}
                </span>
              </TableCell>
              <TableCell className={cn("py-1.5 text-right text-xs tabular-nums", row.score < 0 ? "text-destructive" : "text-success")}>
                {row.score >= 0 ? "+" : ""}
                {formatNumber(row.score, 3)}
              </TableCell>
              <TableCell className="py-1.5 pr-3 text-right">
                {action && <Badge variant={action === "sell" ? "destructive" : action === "buy" ? "default" : "secondary"}>{PLAN_LABEL[action]}</Badge>}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
