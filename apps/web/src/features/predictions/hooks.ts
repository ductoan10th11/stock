import { useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api-client"

import type { LatestPredictions, SymbolPredictions } from "./types"

const STALE_MS = 60_000

export const latestPredictionsQuery = {
  queryKey: ["predictions"],
  queryFn: () => api<LatestPredictions>("/predictions"),
  staleTime: STALE_MS,
}

export const symbolPredictionsQuery = (symbol: string) => ({
  queryKey: ["predictions", symbol],
  queryFn: () => api<SymbolPredictions>(`/predictions/${symbol}?days=90`),
  staleTime: STALE_MS,
})

export const useLatestPredictions = () => useQuery(latestPredictionsQuery)

/** No placeholder data: after a click the panel must show a skeleton, never the previous symbol. */
export const useSymbolPredictions = (symbol: string | undefined) =>
  useQuery({ ...symbolPredictionsQuery(symbol ?? ""), enabled: Boolean(symbol) })

export function usePrefetchSymbol() {
  const client = useQueryClient()
  return (symbol: string) => void client.prefetchQuery(symbolPredictionsQuery(symbol))
}
