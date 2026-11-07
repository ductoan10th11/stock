import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatNumber, formatPercent } from "@/lib/format"

import type { MetricsRow } from "../types"

type Column = { key: keyof MetricsRow; label: string; kind: "percent" | "ratio" | "count" }

export const SUMMARY_COLUMNS: Column[] = [
  { key: "return_ann", label: "Lợi suất năm", kind: "percent" },
  { key: "total_return", label: "Tổng lợi suất", kind: "percent" },
  { key: "sharpe", label: "Sharpe", kind: "ratio" },
  { key: "max_drawdown", label: "Sụt giảm tối đa", kind: "percent" },
  { key: "alpha_ann", label: "Alpha năm", kind: "percent" },
  { key: "avg_holdings", label: "Số mã TB", kind: "count" },
]

export const FULL_COLUMNS: Column[] = [
  ...SUMMARY_COLUMNS,
  { key: "alpha_ci_low", label: "Alpha CI thấp", kind: "percent" },
  { key: "alpha_ci_high", label: "Alpha CI cao", kind: "percent" },
  { key: "alpha_adj_low", label: "CI thấp (đa kiểm định)", kind: "percent" },
  { key: "alpha_adj_high", label: "CI cao (đa kiểm định)", kind: "percent" },
  { key: "beta", label: "Beta", kind: "ratio" },
  { key: "turnover_per_day", label: "Vòng quay mua/ngày", kind: "percent" },
]

const render = (value: number | null, kind: Column["kind"]) =>
  kind === "percent" ? formatPercent(value) : formatNumber(value, kind === "ratio" ? 2 : 1)

export function MetricsTable({ rows, columns, pendingLabel }: { rows: MetricsRow[]; columns: Column[]; pendingLabel?: string }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Chiến thuật</TableHead>
          {columns.map((column) => (
            <TableHead key={column.key} className="text-right">
              {column.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.key}>
            <TableCell className="font-medium">{row.label}</TableCell>
            {columns.map((column) => (
              <TableCell key={column.key} className="text-right tabular-nums">
                {render(row[column.key] as number | null, column.kind)}
              </TableCell>
            ))}
          </TableRow>
        ))}
        {pendingLabel && (
          <TableRow>
            <TableCell className="font-medium">{pendingLabel}</TableCell>
            {columns.map((column) => (
              <TableCell key={column.key} className="text-right">
                <Skeleton className="ml-auto h-4 w-12" />
              </TableCell>
            ))}
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
