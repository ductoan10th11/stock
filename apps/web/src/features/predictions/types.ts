export type Direction = "up" | "flat" | "down"

export type Probabilities = { p_down: number; p_flat: number; p_up: number; direction: Direction }

export type PredictionRow = Probabilities & { symbol: string; rank: number; score: number }

export type LatestPredictions = { date: string; trained_until: string; in_sample: boolean; rows: PredictionRow[] }

export type Candle = { date: string; open: number; high: number; low: number; close: number }

export type DailyPrediction = Probabilities & { date: string; source: "oos" | "live"; correct: boolean | null }

export type SymbolPredictions = {
  symbol: string
  trained_until: string
  last_oos_date: string
  candles: Candle[]
  predictions: DailyPrediction[]
  next_session: DailyPrediction | null
  hit_rate: { correct: number; total: number } | null
}

export const DIRECTION_LABEL: Record<Direction, string> = { up: "Tăng", flat: "Đi ngang", down: "Giảm" }

export const probabilityOf = (p: Probabilities) => ({ up: p.p_up, flat: p.p_flat, down: p.p_down })[p.direction]
