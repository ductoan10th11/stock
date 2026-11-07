import { useState } from "react"

import { HelpTip } from "@/components/help-tip"
import { SliderField } from "@/components/slider-field"
import { CollapsibleSection } from "@/components/collapsible-section"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Meta } from "@/features/meta/types"
import { BlendWeights } from "@/features/portfolio/blend-weights"
import { PortfolioFields } from "@/features/portfolio/portfolio-fields"
import { defaultBlendWeights, defaultPortfolio, toPortfolioParams } from "@/features/portfolio/types"
import { formatDate, formatVnd } from "@/lib/format"

import { useCreateAccount } from "../hooks"
import type { PaperState } from "../types"

type Props = { meta: Meta; state: PaperState }

export function CreateAccountForm({ meta, state }: Props) {
  const [strategy, setStrategy] = useState("model")
  const [blendWeights, setBlendWeights] = useState(() => defaultBlendWeights(meta.blend_members))
  const [capital, setCapital] = useState(1_000_000_000)
  const [portfolio, setPortfolio] = useState(() => defaultPortfolio(2))
  const [slippage, setSlippage] = useState(10)
  const [replay, setReplay] = useState(false)
  const create = useCreateAccount()

  const selected = meta.strategies.find((item) => item.id === strategy)!
  const weights = strategy === "blend" ? blendWeights : { [strategy]: 1 }
  const usesModel = (weights.model ?? 0) > 0
  const latest = state.latest_candle!
  const problem = !Object.values(weights).some((weight) => weight > 0)
    ? "Cần ít nhất một trọng số khác 0."
    : usesModel && latest <= state.trained_until && !replay
      ? `Phiên mới nhất ${formatDate(latest)} chưa sau ngày huấn luyện ${formatDate(state.trained_until)}. Chờ phiên đóng cửa kế tiếp hoặc chọn chiến thuật không dùng mô hình AI.`
      : null

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Tạo tài khoản giả lập</CardTitle>
        <CardDescription>Chọn chiến thuật và vốn ban đầu. Các thiết lập danh mục đã có giá trị mặc định hợp lý, chỉ chỉnh khi cần.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label>Chiến thuật</Label>
          <Select value={strategy} onValueChange={setStrategy}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {meta.strategies.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{selected.help}</p>
        </div>
        {strategy === "blend" && (
          <BlendWeights
            members={meta.strategies.filter((item) => meta.blend_members.includes(item.id))}
            weights={blendWeights}
            onChange={setBlendWeights}
          />
        )}
        <div className="space-y-2">
          <Label htmlFor="paper-capital" className="gap-1.5">
            Vốn ban đầu (VND)
            <HelpTip>Số tiền ảo bắt đầu của tài khoản.</HelpTip>
          </Label>
          <Input
            id="paper-capital"
            type="number"
            min={10_000_000}
            max={100_000_000_000}
            step={100_000_000}
            value={capital}
            onChange={(event) => setCapital(Number(event.target.value))}
          />
          <p className="text-xs text-muted-foreground">{formatVnd(capital)}</p>
        </div>
        <CollapsibleSection title="Cài đặt danh mục nâng cao">
          <PortfolioFields value={portfolio} onChange={setPortfolio} modelApplies={strategy === "model"} />
          <SliderField
            label="Trượt giá mỗi chiều (bps)"
            value={slippage}
            onChange={setSlippage}
            min={0}
            max={50}
            step={5}
            help="Chênh lệch giữa giá dự kiến và giá khớp thực tế. 10 bps = 0,1%."
          />
        </CollapsibleSection>
        <div className="flex items-start gap-2 rounded-lg border p-3">
          <Checkbox id="replay" checked={replay} onCheckedChange={(checked) => setReplay(checked === true)} className="mt-0.5" />
          <Label htmlFor="replay" className="flex-col items-start gap-0.5">
            Chạy lại 5 phiên gần nhất{state.replay_start ? ` (từ ${formatDate(state.replay_start)})` : ""}
            <span className="text-xs font-normal text-muted-foreground">
              Cho tài khoản giao dịch ngay theo nến đã có để xem cách chiến thuật vận hành. Điểm các ngày trước ngày huấn luyện là điểm trong mẫu, nên kết quả không phản ánh khả năng thật.
            </span>
          </Label>
        </div>
        {problem && (
          <Alert>
            <AlertDescription>{problem}</AlertDescription>
          </Alert>
        )}
        <Button
          disabled={problem !== null || create.isPending}
          onClick={() =>
            create.mutate({ strategy, blend_weights: strategy === "blend" ? blendWeights : {}, capital, slippage_bps: slippage, params: toPortfolioParams(portfolio), replay })
          }
        >
          {create.isPending ? (replay ? "Đang chạy lại..." : "Đang tạo...") : replay && state.replay_start ? `Chạy lại từ phiên ${formatDate(state.replay_start)}` : `Bắt đầu từ phiên ${formatDate(latest)}`}
        </Button>
      </CardContent>
    </Card>
  )
}
