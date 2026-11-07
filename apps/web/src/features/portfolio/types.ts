export type Sizing = "equal" | "score"
export type Exit = "signal" | "rank"

export type PortfolioParams = {
  top_fraction: number
  buffer: number
  min_hold: number
  min_score: number | null
  sizing: Sizing
  sell_score: number | null
}

export type PortfolioForm = {
  topPercent: number
  buffer: number
  minHold: number
  onlyProfitable: boolean
  buyScore: number
  exit: Exit
  sellScore: number
  sizing: Sizing
}

/** The configuration chosen on the development period (to 2024) of the walk-forward scores, see docs/flow.md B16. */
export const defaultPortfolio = (minHold: number): PortfolioForm => ({
  topPercent: 10,
  buffer: 2,
  minHold,
  onlyProfitable: true,
  buyScore: 0.06,
  exit: "signal",
  sellScore: -0.1,
  sizing: "equal",
})

export const toPortfolioParams = (form: PortfolioForm): PortfolioParams => ({
  top_fraction: form.topPercent / 100,
  buffer: form.buffer,
  min_hold: form.minHold,
  min_score: form.onlyProfitable || form.sizing === "score" ? form.buyScore : null,
  sizing: form.sizing,
  sell_score: form.exit === "signal" ? form.sellScore : null,
})

export const defaultBlendWeights = (members: string[]): Record<string, number> =>
  Object.fromEntries(members.map((member) => [member, 1]))

const signed = (value: number) => `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(2).replace(".", ",")}`

export function describeRules(params: PortfolioParams): string {
  const buy = params.min_score === null ? "mua theo xếp hạng" : `mua khi điểm ≥ ${signed(params.min_score)}`
  const sell = params.sell_score === null ? "bán khi tụt hạng" : `bán khi điểm ≤ ${signed(params.sell_score)}`
  return `${buy}, ${sell}, ${params.sizing === "score" ? "chia vốn theo điểm" : "chia đều"}`
}
