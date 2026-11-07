import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { lazy, Suspense } from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"

import { Layout } from "./layout"
import { prefetchBacktestPage } from "./prefetch"

const BacktestPage = lazy(() => import("@/pages/backtest-page").then((module) => ({ default: module.BacktestPage })))
const PaperPage = lazy(() => import("@/pages/paper-page").then((module) => ({ default: module.PaperPage })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

if (window.location.pathname === "/") prefetchBacktestPage(queryClient)

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Suspense>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<BacktestPage />} />
                <Route path="paper" element={<PaperPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
