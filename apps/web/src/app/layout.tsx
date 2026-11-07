import { useQueryClient } from "@tanstack/react-query"
import { ChartCandlestick, Wallet } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"

import { cn } from "@/lib/utils"

import { prefetchBacktestPage, prefetchPaperPage } from "./prefetch"

const links = [
  { to: "/", label: "Backtest", icon: ChartCandlestick },
  { to: "/paper", label: "Paper Trading", icon: Wallet },
]

export function Layout() {
  const client = useQueryClient()
  const warm = (to: string) => (to === "/paper" ? prefetchPaperPage(client) : prefetchBacktestPage(client))
  return (
    <div className="min-h-svh md:grid md:h-svh md:grid-cols-[13rem_1fr] md:overflow-hidden">
      <aside className="border-b bg-card md:border-r md:border-b-0">
        <div className="px-4 py-3 text-lg font-medium md:py-5">Stock ML</div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              onPointerEnter={() => warm(to)}
              onFocus={() => warm(to)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm whitespace-nowrap text-muted-foreground hover:bg-accent hover:text-foreground",
                  isActive && "bg-accent font-medium text-foreground",
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-h-0 min-w-0 px-4 py-4 md:px-6 md:py-5">
        <div className="mx-auto flex h-full max-w-[1400px] flex-col">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
