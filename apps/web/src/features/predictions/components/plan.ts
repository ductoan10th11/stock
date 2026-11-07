import type { PaperState } from "@/features/paper/types"

export type Plan = "held" | "buy" | "sell"

export const PLAN_LABEL: Record<Plan, string> = { held: "đang giữ", buy: "sẽ mua", sell: "sẽ bán" }

export function planOf(state: PaperState | undefined): Record<string, Plan> {
  const plan: Record<string, Plan> = {}
  state?.positions.forEach((position) => (plan[position.symbol] = "held"))
  state?.orders.forEach((order) => {
    if (order.action !== "hold") plan[order.symbol] = order.action
  })
  return plan
}
