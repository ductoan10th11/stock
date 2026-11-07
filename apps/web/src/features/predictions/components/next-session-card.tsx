import type { CSSProperties } from "react"
import { ArrowDown, ArrowUp, Minus } from "lucide-react"

import { HelpTip } from "@/components/help-tip"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { DOWN_COLOR, FLAT_COLOR, UP_COLOR } from "@/lib/colors"
import { formatNumber, formatPercent } from "@/lib/format"

import { DIRECTION_LABEL, probabilityOf, type PredictionRow, type SymbolPredictions } from "../types"
import { PLAN_LABEL, type Plan } from "./plan"

const ICON = { up: [ArrowUp, UP_COLOR], down: [ArrowDown, DOWN_COLOR], flat: [Minus, FLAT_COLOR] } as const

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="grid grid-cols-[3.5rem_1fr_2.25rem] items-center gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <Progress value={value * 100} className="h-1.5 bg-muted *:data-[slot=progress-indicator]:bg-(--bar)" style={{ "--bar": color } as CSSProperties} />
      <span className="text-right tabular-nums">{formatPercent(value, 0)}</span>
    </div>
  )
}

type Props = { data: SymbolPredictions; row: PredictionRow | undefined; plan: Plan | undefined; total: number }

export function NextSessionCard({ data, row, plan, total }: Props) {
  const next = data.next_session
  if (!next) {
    return (
      <Card className="shrink-0 gap-0 py-3">
        <CardContent className="text-sm text-muted-foreground">Chưa có dự đoán cho phiên tới của {data.symbol}. Bấm Cập nhật dữ liệu.</CardContent>
      </Card>
    )
  }
  const [Icon, color] = ICON[next.direction]
  const negative = row !== undefined && row.score < 0
  const hit = data.hit_rate
  return (
    <Card className="shrink-0 gap-0 py-3">
      <CardContent className="grid items-center gap-x-8 gap-y-3 md:grid-cols-[auto_minmax(0,1fr)_minmax(0,1.3fr)]">
        <div>
          <div className="text-xs text-muted-foreground">{data.symbol} · dự đoán phiên tới</div>
          <div className="flex items-center gap-2 text-2xl font-medium" style={{ color }}>
            <Icon className="size-6" />
            {DIRECTION_LABEL[next.direction]}
          </div>
          <div className="text-xs text-muted-foreground tabular-nums">xác suất {formatPercent(probabilityOf(next), 0)}</div>
        </div>
        <div className="space-y-1">
          <Bar label="Giảm" value={next.p_down} color={DOWN_COLOR} />
          <Bar label="Đi ngang" value={next.p_flat} color={FLAT_COLOR} />
          <Bar label="Tăng" value={next.p_up} color={UP_COLOR} />
        </div>
        <div className="space-y-1 text-sm">
          {row && (
            <p>
              Điểm <strong className={negative ? "text-destructive" : "text-success"}>{`${row.score >= 0 ? "+" : ""}${formatNumber(row.score, 3)}`}</strong> · hạng{" "}
              <strong>
                {row.rank}/{total}
              </strong>
              {plan && (
                <>
                  {" "}
                  · paper trading: <strong>{PLAN_LABEL[plan]}</strong>
                </>
              )}
              {negative && (
                <HelpTip>Điểm âm nghĩa là mô hình nghiêng về giảm nhiều hơn tăng. Mã chỉ được mua khi đạt điều kiện của tài khoản (ví dụ "chỉ mua nếu có lãi").</HelpTip>
              )}
            </p>
          )}
          {hit && (
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              Đoán đúng {hit.correct}/{hit.total} phiên ({formatPercent(hit.correct / hit.total, 0)}) trên biểu đồ; ngẫu nhiên khoảng 33 đến 36%
              <HelpTip>Chỉ một mã trong vài tháng nên dao động nhiều. Trên toàn bộ dữ liệu, mô hình chỉ hơn đoán ngẫu nhiên rất ít.</HelpTip>
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
