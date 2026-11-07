import { ChevronDown } from "lucide-react"
import type { ReactNode } from "react"

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

type Props = { title: string; children: ReactNode; defaultOpen?: boolean }

export function CollapsibleSection({ title, children, defaultOpen = false }: Props) {
  return (
    <Collapsible defaultOpen={defaultOpen} className="group rounded-lg border">
      <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium">
        {title}
        <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-4 border-t px-3 py-4">{children}</CollapsibleContent>
    </Collapsible>
  )
}
