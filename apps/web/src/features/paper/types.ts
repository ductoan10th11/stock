import type { PortfolioParams } from "@/features/portfolio/types"

export type AccountInfo = {
  id: number
  replay: boolean
  weights: Record<string, number>
  params: PortfolioParams
  initial_capital: number
  slippage_bps: number
  start_date: string
  last_date: string
}

export type Summary = {
  equity: number
  cash: number
  gain: number
  gain_pct: number
  cash_pct: number
  equal_weight_return: number | null
  vnindex_return: number | null
}

export type EquityCurve = {
  dates: string[]
  account: number[]
  equal_weight: number[]
  vnindex: number[] | null
}

export type Order = { symbol: string; action: "buy" | "sell" | "hold"; shares: number; price: number; value: number }
export type Position = { symbol: string; shares: number; cost: number; price: number; pnl_pct: number; value: number; held: number }
export type RankingRow = { rank: number; symbol: string; score: number; held: boolean }
export type Trade = {
  date: string
  symbol: string
  side: "buy" | "sell"
  shares: number
  price: number
  value: number
  fee: number
  entry_price: number | null
  entry_value: number | null
  pnl: number | null
  pnl_pct: number | null
}

export type PaperState = {
  data_ready: boolean
  trained_until: string
  latest_candle: string | null
  replay_start: string | null
  account: AccountInfo | null
  score_ready: boolean
  signal_date: string | null
  summary: Summary | null
  equity: EquityCurve | null
  orders: Order[]
  positions: Position[]
  ranking: RankingRow[]
  trades: Trade[]
}

export type CreateAccountRequest = {
  strategy: string
  blend_weights: Record<string, number>
  capital: number
  slippage_bps: number
  params: PortfolioParams
  replay?: boolean
}
