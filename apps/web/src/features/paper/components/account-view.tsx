import { Alert, AlertDescription } from "@/components/ui/alert"
import { strategyLabel } from "@/features/meta/hooks"
import type { Meta } from "@/features/meta/types"
import { describeRules } from "@/features/portfolio/types"
import { formatDate } from "@/lib/format"

import type { PaperState } from "../types"
import { HoldingsCard } from "./holdings-card"
import { OrdersCard } from "./orders-card"
import { Overview } from "./overview"

export function AccountOverview({ meta, state }: { meta: Meta; state: PaperState }) {
  const account = state.account!
  const strategy = Object.entries(account.weights)
    .filter(([, weight]) => weight)
    .map(([id, weight]) => (Object.keys(account.weights).length > 1 ? `${strategyLabel(meta, id)} ×${weight}` : strategyLabel(meta, id)))
    .join(" + ")
  const modelOnly = account.weights.model === 1 && Object.keys(account.weights).length === 1
  const rules = modelOnly ? ` · ${describeRules(account.params)}` : ""
  const stale = state.score_ready && state.signal_date! < state.latest_candle!
  return (
    <div className="flex flex-col gap-3 lg:h-full">
      {!state.score_ready && (
        <Alert>
          <AlertDescription>Thiếu nhật ký dự đoán của mô hình AI. Bấm Cập nhật dữ liệu.</AlertDescription>
        </Alert>
      )}
      {stale && (
        <Alert>
          <AlertDescription>
            Tín hiệu mới nhất là {formatDate(state.signal_date!)} nhưng nến mới nhất là {formatDate(state.latest_candle!)}. Bấm Cập nhật dữ liệu để chấm điểm phiên còn thiếu.
          </AlertDescription>
        </Alert>
      )}
      <div className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Overview account={account} strategy={strategy + rules} summary={state.summary} equity={state.equity} orders={state.orders} />
        <div className="flex min-h-0 flex-col gap-4">
          <HoldingsCard positions={state.positions} summary={state.summary} initialCapital={account.initial_capital} className="lg:max-h-[42%]" />
          <OrdersCard orders={state.orders} ranking={state.ranking} equity={state.summary?.equity ?? account.initial_capital} className="lg:flex-1" />
        </div>
      </div>
    </div>
  )
}
