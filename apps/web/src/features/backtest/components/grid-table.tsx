import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatPercent } from "@/lib/format"

import type { Table as TableData } from "../types"

export function PercentGrid({ table }: { table: TableData }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Chiến thuật</TableHead>
          {table.columns.map((column) => (
            <TableHead key={column} className="text-right">
              {column}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {table.rows.map((row) => (
          <TableRow key={row.label}>
            <TableCell className="font-medium">{row.label}</TableCell>
            {row.values.map((value, index) => (
              <TableCell key={table.columns[index]} className="text-right tabular-nums">
                {formatPercent(value)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
