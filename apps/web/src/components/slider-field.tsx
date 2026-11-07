import { HelpTip } from "@/components/help-tip"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"

type Props = {
  label: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  format?: (value: number) => string
  help?: string
  disabled?: boolean
}

export function SliderField({ label, value, onChange, min, max, step, format = String, help, disabled }: Props) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label className="gap-1.5">
          {label}
          {help && <HelpTip>{help}</HelpTip>}
        </Label>
        <span className="text-sm tabular-nums text-muted-foreground">{format(value)}</span>
      </div>
      <Slider aria-label={label} value={[value]} onValueChange={([next]) => onChange(next)} min={min} max={max} step={step} disabled={disabled} />
    </div>
  )
}
