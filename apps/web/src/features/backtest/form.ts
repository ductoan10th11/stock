import type { Meta, Preset } from "@/features/meta/types"
import { defaultBlendWeights, defaultPortfolio, toPortfolioParams, type PortfolioForm } from "@/features/portfolio/types"

import type { BacktestRequest, Execution, Period } from "./types"

export type BacktestForm = {
  execution: Execution
  strategies: string[]
  blendWeights: Record<string, number>
  period: Period
  feeScale: number
  slippageBps: number
  limits: boolean
  capital: number
  portfolio: PortfolioForm
}

export const DEFAULT_STRATEGIES = ["model", "momentum_12_1", "low_volatility"]

export function presetDefaults(preset: Preset): Pick<BacktestForm, "execution" | "feeScale" | "slippageBps" | "limits" | "capital" | "portfolio"> {
  return {
    execution: preset.id,
    feeScale: 1,
    slippageBps: preset.slippage_bps,
    limits: preset.limits,
    capital: 1_000_000_000,
    portfolio: defaultPortfolio(preset.min_hold),
  }
}

export function initialForm(meta: Meta): BacktestForm {
  return {
    ...presetDefaults(meta.presets[0]),
    strategies: DEFAULT_STRATEGIES,
    blendWeights: defaultBlendWeights(meta.blend_members),
    period: "all",
  }
}

export type FormProblem = "no_strategy" | "no_blend_weight"

export function formProblem(form: BacktestForm): FormProblem | null {
  if (form.strategies.length === 0) return "no_strategy"
  if (form.strategies.includes("blend") && !Object.values(form.blendWeights).some((weight) => weight > 0)) return "no_blend_weight"
  return null
}

export function toRequest(form: BacktestForm): BacktestRequest {
  return {
    strategies: form.strategies,
    blend_weights: form.strategies.includes("blend") ? form.blendWeights : {},
    execution: form.execution,
    period: form.period,
    fee_scale: form.feeScale,
    slippage_bps: form.slippageBps,
    limits: form.limits,
    capital: form.capital,
    params: toPortfolioParams(form.portfolio),
  }
}
