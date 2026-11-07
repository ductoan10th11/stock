import type { QueryClient } from "@tanstack/react-query"

import { backtestQuery, randomQuery } from "@/features/backtest/hooks"
import { initialForm, toRequest } from "@/features/backtest/form"
import { metaQuery } from "@/features/meta/hooks"
import { paperQuery } from "@/features/paper/hooks"
import { latestPredictionsQuery, symbolPredictionsQuery } from "@/features/predictions/hooks"

/** Warm the cache so the Paper Trading tabs open with data already there. */
export function prefetchPaperPage(client: QueryClient) {
  void client.prefetchQuery(metaQuery)
  void client.prefetchQuery(paperQuery)
  client
    .fetchQuery(latestPredictionsQuery)
    .then((latest) => client.prefetchQuery(symbolPredictionsQuery(latest.rows[0].symbol)))
    .catch(() => undefined)
}

/** Start the default backtest before the page code has even loaded; the page then finds it in the cache. */
export function prefetchBacktestPage(client: QueryClient) {
  client
    .fetchQuery(metaQuery)
    .then((meta) => {
      if (!meta.backtest_ready) return
      const request = toRequest(initialForm(meta))
      return client.prefetchQuery(backtestQuery(request)).then(() => client.prefetchQuery(randomQuery(request)))
    })
    .catch(() => undefined)
}
