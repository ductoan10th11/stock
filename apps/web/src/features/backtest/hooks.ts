import { keepPreviousData, useQuery } from "@tanstack/react-query"

import type { SymbolPredictions } from "@/features/predictions/types"
import { api, post } from "@/lib/api-client"

import type { BacktestRequest, BacktestResponse, MetricsRow, ReviewList, ReviewWindow } from "./types"

export const backtestQuery = (request: BacktestRequest) => ({
  queryKey: ["backtest", request],
  queryFn: () => post<BacktestResponse>("/backtest", request),
  staleTime: Infinity,
})

/** Only the fields the random baseline depends on, so toggling strategies does not rerun it. */
const randomKey = (request: BacktestRequest) => [request.params, request.execution, request.period, request.fee_scale, request.slippage_bps, request.limits, request.capital]

export const randomQuery = (request: BacktestRequest) => ({
  queryKey: ["backtest-random", ...randomKey(request)],
  queryFn: () => post<MetricsRow>("/backtest/random", request),
  staleTime: Infinity,
})

export const useBacktest = (request: BacktestRequest | null) =>
  useQuery({ ...backtestQuery(request!), enabled: request !== null, placeholderData: keepPreviousData })

/** Waits for the main result: both run in the same server process and would slow each other down. */
export const useRandomBaseline = (request: BacktestRequest, mainReady: boolean) =>
  useQuery({ ...randomQuery(request), enabled: mainReady, placeholderData: keepPreviousData })

const windowQuery = (window: ReviewWindow) => new URLSearchParams(Object.entries(window).filter(([, value]) => value) as [string, string][]).toString()

/** The walk-forward predictions never change while the server runs, so they are cached for good. */
export const reviewListQuery = (window: ReviewWindow) => ({
  queryKey: ["review", window],
  queryFn: () => api<ReviewList>(`/backtest/predictions?${windowQuery(window)}`),
  staleTime: Infinity,
})

export const reviewSymbolQuery = (symbol: string, window: ReviewWindow) => ({
  queryKey: ["review", symbol, window],
  queryFn: () => api<SymbolPredictions>(`/backtest/predictions/${symbol}?${windowQuery(window)}`),
  staleTime: Infinity,
})

export const useReviewList = (window: ReviewWindow) => useQuery({ ...reviewListQuery(window), placeholderData: keepPreviousData })

/** No placeholder data: after a click or a new window the panel shows a skeleton, never the previous chart. */
export const useReviewSymbol = (symbol: string | undefined, window: ReviewWindow) =>
  useQuery({ ...reviewSymbolQuery(symbol ?? "", window), enabled: Boolean(symbol) })
