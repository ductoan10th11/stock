import { HelpTip } from "@/components/help-tip"
import { SliderField } from "@/components/slider-field"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

import type { Exit, PortfolioForm, Sizing } from "./types"

type Props = { value: PortfolioForm; onChange: (value: PortfolioForm) => void; modelApplies?: boolean }

const score = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2).replace(".", ",")}`

function Choice<T extends string>({ name, value, options, onChange, disabled }: { name: string; value: T; options: { id: T; label: string; hint: string }[]; onChange: (id: T) => void; disabled: boolean }) {
  return (
    <RadioGroup value={value} onValueChange={(id) => onChange(id as T)} disabled={disabled} className="flex flex-wrap gap-x-5 gap-y-1">
      {options.map((option) => (
        <div key={option.id} className="flex items-center gap-2" title={option.hint}>
          <RadioGroupItem id={`${name}-${option.id}`} value={option.id} />
          <Label htmlFor={`${name}-${option.id}`} className="font-normal">
            {option.label}
          </Label>
        </div>
      ))}
    </RadioGroup>
  )
}

export function PortfolioFields({ value, onChange, modelApplies = true }: Props) {
  const patch = (change: Partial<PortfolioForm>) => onChange({ ...value, ...change })
  const byScore = value.sizing === "score"
  const bySignal = value.exit === "signal"
  return (
    <div className="space-y-4">
      <SliderField
        label="Số mã nắm giữ (% trong 19 mã)"
        value={value.topPercent}
        onChange={(topPercent) => patch({ topPercent })}
        min={10}
        max={50}
        step={5}
        format={(v) => `${v}%`}
        help="Tối đa bao nhiêu mã được giữ cùng lúc (ít nhất 3 mã). Ít mã thì tập trung hơn, nhiều mã thì an toàn hơn."
      />
      <SliderField
        label="Số phiên giữ tối thiểu"
        value={value.minHold}
        onChange={(minHold) => patch({ minHold })}
        min={1}
        max={10}
        step={1}
        help="Quy định T+2 của sàn: mua xong phải chờ 2 phiên mới bán được. Giữ lâu hơn thì ít giao dịch và ít phí hơn."
      />
      <div className="space-y-4 rounded-lg border p-3">
        <p className="text-xs font-medium">Quy tắc Mô hình AI{!modelApplies && " (chọn Mô hình AI để dùng)"}</p>
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Checkbox
              id="only-profitable"
              checked={value.onlyProfitable || byScore}
              disabled={!modelApplies || byScore}
              onCheckedChange={(checked) => patch({ onlyProfitable: checked === true })}
            />
            <Label htmlFor="only-profitable" className="gap-1.5">
              Chỉ xác nhận mua nếu có lãi
              <HelpTip>Chỉ mua mã mà mô hình dự đoán tăng nhiều hơn giảm (điểm lớn hơn 0), và đủ mạnh theo mức bên dưới. Mã chưa đạt thì giữ tiền mặt. Chia vốn theo điểm luôn bật quy tắc này.</HelpTip>
            </Label>
          </div>
          <SliderField
            label="Mua khi điểm từ"
            value={value.buyScore}
            onChange={(buyScore) => patch({ buyScore })}
            min={0}
            max={0.15}
            step={0.01}
            format={score}
            disabled={!modelApplies || !(value.onlyProfitable || byScore)}
            help="Điểm = xác suất tăng trừ xác suất giảm. 0 nghĩa là chỉ cần dự đoán có lãi; mức cao hơn đòi tín hiệu mạnh hơn, ít mua hơn."
          />
        </div>
        <div className="space-y-2">
          <Label className="gap-1.5">
            Cách bán
            <HelpTip>Theo tín hiệu: giữ mã cho đến khi mô hình thật sự xấu đi. Theo xếp hạng: bán khi mã tụt khỏi nhóm đầu bảng, tín hiệu dao động nên phải mua bán gần như mỗi ngày và phí ăn hết lãi.</HelpTip>
          </Label>
          <Choice<Exit>
            name="exit"
            value={value.exit}
            disabled={!modelApplies}
            onChange={(exit) => patch({ exit })}
            options={[
              { id: "signal", label: "Theo tín hiệu", hint: "giữ đến khi điểm xuống dưới ngưỡng bán" },
              { id: "rank", label: "Theo xếp hạng", hint: "bán khi tụt khỏi nhóm đầu bảng (mua bán nhiều, tốn phí)" },
            ]}
          />
          {bySignal ? (
            <SliderField
              label="Bán khi điểm xuống dưới"
              value={value.sellScore}
              onChange={(sellScore) => patch({ sellScore })}
              min={-0.3}
              max={0}
              step={0.01}
              format={score}
              disabled={!modelApplies}
              help="Ngưỡng càng sâu (âm nhiều) thì càng ít bán, ít phí nhưng chịu sụt giảm lâu hơn. Ngưỡng nông (gần 0) bán quá sớm: trong thử nghiệm, −0,06 cho kết quả âm ở giai đoạn xác nhận."
            />
          ) : (
            <SliderField
              label="Mức kiên nhẫn khi đổi mã"
              value={value.buffer}
              onChange={(buffer) => patch({ buffer })}
              min={1}
              max={3}
              step={0.5}
              format={(v) => v.toFixed(1)}
              help="1 = mỗi ngày chọn lại nhóm đầu bảng. Cao hơn = chỉ bán khi mã tụt xa khỏi nhóm đầu."
            />
          )}
        </div>
        <div className="space-y-2">
          <Label className="gap-1.5">
            Cách chia vốn
            <HelpTip>Theo điểm: mã điểm cao nhận nhiều vốn hơn, theo tỷ lệ điểm. Chia đều: mỗi mã một phần bằng nhau. Trong thử nghiệm, chia đều cho kết quả tốt hơn một chút. Vốn chỉ được chia lúc mua vào.</HelpTip>
          </Label>
          <Choice<Sizing>
            name="sizing"
            value={value.sizing}
            disabled={!modelApplies}
            onChange={(sizing) => patch({ sizing })}
            options={[
              { id: "equal", label: "Chia đều", hint: "mỗi mã một phần bằng nhau" },
              { id: "score", label: "Theo điểm", hint: "xác suất lãi càng cao, vốn càng nhiều" },
            ]}
          />
        </div>
      </div>
    </div>
  )
}
