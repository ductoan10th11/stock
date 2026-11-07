import { CircleHelp } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

export function HelpTip({ children }: { children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button type="button" variant="ghost" size="icon" aria-label="Giải thích" className="size-5 rounded-full text-muted-foreground hover:bg-transparent">
          <CircleHelp className="size-3.5" />
        </Button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-pretty">{children}</TooltipContent>
    </Tooltip>
  )
}
