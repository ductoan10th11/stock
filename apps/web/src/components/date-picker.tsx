import { CalendarIcon } from "lucide-react"
import { vi } from "react-day-picker/locale"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { formatDate } from "@/lib/format"
import { cn } from "@/lib/utils"

type Props = { className?: string; label: string; value: string | undefined; min: string | undefined; max: string | undefined; onChange: (iso: string) => void }

const toDate = (iso: string) => {
  const [year, month, day] = iso.split("-").map(Number)
  return new Date(year, month - 1, day)
}
const toIso = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`

export function DatePicker({ className, label, value, min, max, onChange }: Props) {
  const selected = value ? toDate(value) : undefined
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" aria-label={label} disabled={!value} className={cn("w-32 justify-start font-normal tabular-nums", className)}>
          <CalendarIcon />
          {value ? formatDate(value) : "..."}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        {min && max && (
          <Calendar
            mode="single"
            locale={vi}
            formatters={{ formatMonthDropdown: (date) => `Tháng ${date.getMonth() + 1}` }}
            captionLayout="dropdown"
            selected={selected}
            defaultMonth={selected}
            startMonth={toDate(min)}
            endMonth={toDate(max)}
            disabled={{ before: toDate(min), after: toDate(max) }}
            onSelect={(date) => date && onChange(toIso(date))}
          />
        )}
      </PopoverContent>
    </Popover>
  )
}
