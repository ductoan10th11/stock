import { HelpTip } from "@/components/help-tip"
import { SliderField } from "@/components/slider-field"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import type { Meta } from "@/features/meta/types"
import { BlendWeights } from "@/features/portfolio/blend-weights"
import { PortfolioFields } from "@/features/portfolio/portfolio-fields"

import type { BacktestForm } from "../form"

type Props = { meta: Meta; form: BacktestForm; onChange: (form: BacktestForm) => void }

export function AdvancedSettings({ meta, form, onChange }: Props) {
  const patch = (change: Partial<BacktestForm>) => onChange({ ...form, ...change })
  return (
    <div className="space-y-5">
      <SliderField
        label="Mức phí giao dịch"
        value={form.feeScale}
        onChange={(feeScale) => patch({ feeScale })}
        min={0}
        max={2}
        step={0.25}
        format={(v) => `×${v.toFixed(2)}`}
        help="×1 = phí mua 0,15% và bán 0,25%. ×2 là gấp đôi, ×0 là không phí."
      />
      <SliderField
        label="Trượt giá mỗi chiều (bps)"
        value={form.slippageBps}
        onChange={(slippageBps) => patch({ slippageBps })}
        min={0}
        max={50}
        step={5}
        help="Chênh lệch giữa giá dự kiến và giá khớp thực tế. 10 bps = 0,1%."
      />
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor="limits" className="gap-1.5">
          Giá trần/sàn và thanh khoản
          <HelpTip>Giá trần/sàn ±7%: mã mở cửa kịch trần thì không mua được, kịch sàn thì không bán được. Thanh khoản: mỗi mã chỉ chiếm tối đa 10% khối lượng giao dịch trung bình 20 phiên.</HelpTip>
        </Label>
        <Switch id="limits" checked={form.limits} onCheckedChange={(limits) => patch({ limits })} />
      </div>
      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="capital" className="gap-1.5">
          Vốn (VND)
          <HelpTip>Chỉ dùng để tính giới hạn thanh khoản.</HelpTip>
        </Label>
        <Input
          id="capital"
          type="number"
          className="w-44 text-right"
          min={10_000_000}
          max={100_000_000_000}
          step={100_000_000}
          value={form.capital}
          disabled={!form.limits}
          onChange={(event) => patch({ capital: Number(event.target.value) })}
        />
      </div>
      {form.strategies.includes("blend") && (
        <BlendWeights
          members={meta.strategies.filter((strategy) => meta.blend_members.includes(strategy.id))}
          weights={form.blendWeights}
          onChange={(blendWeights) => patch({ blendWeights })}
        />
      )}
      <PortfolioFields value={form.portfolio} onChange={(portfolio) => patch({ portfolio })} modelApplies={form.strategies.includes("model")} />
    </div>
  )
}
