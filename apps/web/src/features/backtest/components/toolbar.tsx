import { ChevronDown, SlidersHorizontal } from "lucide-react"

import { HelpTip } from "@/components/help-tip"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import type { Meta } from "@/features/meta/types"
import { cn } from "@/lib/utils"

import { presetDefaults, type BacktestForm } from "../form"
import type { Period } from "../types"
import { AdvancedSettings } from "./advanced-settings"

type Props = { meta: Meta; form: BacktestForm; onChange: (form: BacktestForm) => void; busy: boolean; summary?: string }

function StrategyPicker({ meta, form, onChange }: Pick<Props, "meta" | "form" | "onChange">) {
  const selected = meta.strategies.filter((strategy) => form.strategies.includes(strategy.id))
  const toggle = (id: string, on: boolean) => onChange({ ...form, strategies: on ? [...form.strategies, id] : form.strategies.filter((strategy) => strategy !== id) })
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="h-9 gap-2 font-normal">
          <span className="flex -space-x-1">
            {selected.slice(0, 4).map((strategy) => (
              <span key={strategy.id} className="size-2.5 rounded-full ring-2 ring-background" style={{ background: strategy.color }} />
            ))}
          </span>
          Chiến thuật ({selected.length})
          <ChevronDown className="text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel>So sánh các chiến thuật</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {meta.strategies.map((strategy) => (
          <DropdownMenuCheckboxItem
            key={strategy.id}
            checked={form.strategies.includes(strategy.id)}
            onCheckedChange={(on) => toggle(strategy.id, on)}
            onSelect={(event) => event.preventDefault()}
            title={strategy.help}
          >
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: strategy.color }} />
            {strategy.label}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function Toolbar({ meta, form, onChange, busy, summary }: Props) {
  const preset = meta.presets.find((item) => item.id === form.execution)
  return (
    <Card className="shrink-0 gap-0 py-2" aria-busy={busy}>
      <CardContent className="flex flex-wrap items-center gap-2 px-3">
      <div className="flex items-center gap-1.5">
        <Select
          value={form.execution}
          onValueChange={(id) => {
            const next = meta.presets.find((item) => item.id === id)
            if (next) onChange({ ...form, ...presetDefaults(next) })
          }}
        >
          <SelectTrigger aria-label="Cách khớp lệnh" className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {meta.presets.map((item) => (
              <SelectItem key={item.id} value={item.id}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {preset && <HelpTip>{preset.description}</HelpTip>}
      </div>
      <div className="flex items-center gap-1.5">
        <Select value={form.period} onValueChange={(period) => onChange({ ...form, period: period as Period })}>
          <SelectTrigger aria-label="Giai đoạn" className="w-52">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(meta.periods).map(([id, label]) => (
              <SelectItem key={id} value={id}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <HelpTip>Xác nhận (từ 2025) là giai đoạn chưa dùng để chọn chiến thuật, đáng tin hơn.</HelpTip>
      </div>
      <StrategyPicker meta={meta} form={form} onChange={onChange} />
      {summary && <span className="ml-auto text-xs text-muted-foreground">{summary}</span>}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="outline" className={cn("h-9 gap-2 font-normal", !summary && "ml-auto")}>
            <SlidersHorizontal className="size-4" />
            Nâng cao
          </Button>
        </SheetTrigger>
        <SheetContent onOpenAutoFocus={(event) => event.preventDefault()}>
          <SheetHeader>
            <SheetTitle>Thiết lập nâng cao</SheetTitle>
            <SheetDescription>Phí, trượt giá và quy tắc mua bán. Kết quả cập nhật ngay khi đổi.</SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
            <AdvancedSettings meta={meta} form={form} onChange={onChange} />
          </div>
        </SheetContent>
      </Sheet>
      </CardContent>
    </Card>
  )
}
