export type Strategy = { id: string; label: string; help: string; color: string }

export type Preset = {
  id: "next_open" | "close"
  label: string
  description: string
  min_hold: number
  slippage_bps: number
  limits: boolean
}

export type Meta = {
  strategies: Strategy[]
  blend_members: string[]
  presets: Preset[]
  periods: Record<string, string>
  backtest_ready: boolean
  trained_until: string | null
}
