import { useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api-client"

import type { Meta } from "./types"

export const metaQuery = { queryKey: ["meta"], queryFn: () => api<Meta>("/meta"), staleTime: Infinity }

export const useMeta = () => useQuery(metaQuery)

export function strategyLabel(meta: Meta, id: string): string {
  return meta.strategies.find((strategy) => strategy.id === id)?.label ?? id
}
