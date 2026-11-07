import { CollapsibleSection } from "@/components/collapsible-section"
import { SliderField } from "@/components/slider-field"
import type { Strategy } from "@/features/meta/types"

type Props = {
  members: Strategy[]
  weights: Record<string, number>
  onChange: (weights: Record<string, number>) => void
}

export function BlendWeights({ members, weights, onChange }: Props) {
  return (
    <CollapsibleSection title="Trọng số tổ hợp (0 = bỏ, 2 = gấp đôi)">
      {members.map((member) => (
        <SliderField
          key={member.id}
          label={member.label}
          help={member.help}
          value={weights[member.id] ?? 1}
          onChange={(value) => onChange({ ...weights, [member.id]: value })}
          min={0}
          max={2}
          step={0.25}
          format={(v) => v.toFixed(2)}
        />
      ))}
    </CollapsibleSection>
  )
}
