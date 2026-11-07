import type { PortfolioParams } from "@/features/portfolio/types"

export type Execution = "next_open" | "close"
export type Period = "all" | "dev" | "confirm"

export type BacktestRequest = {
  strategies: string[]
  blend_weights: Record<string, number>
  execution: Execution
  period: Period
  fee_scale: number
  slippage_bps: number
  limits: boolean
  capital: number
  params: PortfolioParams
}

export type MetricsRow = {
  key: string
  label: string
  kind: "strategy" | "benchmark" | "random"
  verdict: "significant" | "insufficient" | "unknown" | null
  return_ann: number | null
  total_return: number | null
  sharpe: number | null
  max_drawdown: number | null
  alpha_ann: number | null
  alpha_ci_low: number | null
  alpha_ci_high: number | null
  alpha_adj_low: number | null
  alpha_adj_high: number | null
  beta: number | null
  avg_holdings: number | null
  turnover_per_day: number | null
}

export type Curve = {
  key: string
  label: string
  color: string
  dash: "solid" | "dash" | "dot"
  wealth: (number | null)[]
  drawdown: (number | null)[]
}

export type Table = { columns: string[]; rows: { label: string; values: (number | null)[] }[] }

export type BacktestResponse = {
  start: string
  end: string
  sessions: number
  dates: string[]
  metrics: MetricsRow[]
  curves: Curve[]
  yearly: Table
  fee_sensitivity: Table
}

export type ReviewWindow = { span?: "week" | "month" | "year"; start?: string; end?: string }

export type ReviewList = {
  start: string
  end: string
  first_date: string
  last_date: string
  correct: number
  total: number
  rows: { symbol: string; correct: number; total: number }[]
}
