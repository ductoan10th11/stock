import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, ReferenceArea, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts"

import { ChartContainer } from "@/components/ui/chart"
import { DOWN_COLOR, FLAT_COLOR, UP_COLOR } from "@/lib/colors"
import { formatDate, formatNumber, formatPercent } from "@/lib/format"

import { DIRECTION_LABEL, probabilityOf, type DailyPrediction, type Direction, type SymbolPredictions } from "../types"
import { Marker } from "./marker"

const FUTURE_ROWS = 10
const COLOR: Record<Direction, string> = { up: UP_COLOR, down: DOWN_COLOR, flat: FLAT_COLOR }
const ARROW: Record<Direction, string> = { up: "▲", down: "▼", flat: "●" }

type Row = {
  key: string
  range?: [number, number]
  open?: number
  close?: number
  changePct?: number
  prediction?: DailyPrediction
  score?: number
}

type CandleProps = { x: number; y: number; width: number; height: number; payload: Row }

function Candle({ x, y, width, height, payload }: CandleProps) {
  const { open, close, range, prediction } = payload
  if (!range || open == null || close == null) return null
  const [low, high] = range
  const toY = (price: number) => (high === low ? y : y + ((high - price) / (high - low)) * height)
  const color = close >= open ? UP_COLOR : DOWN_COLOR
  const top = toY(Math.max(open, close))
  const center = x + width / 2
  return (
    <g>
      <line x1={center} x2={center} y1={y} y2={y + height} stroke={color} strokeWidth={1} />
      <rect x={x} y={top} width={Math.max(width, 2)} height={Math.max(toY(Math.min(open, close)) - top, 1)} fill={color} />
      {prediction && <Marker cx={center} cy={y + height + 10} direction={prediction.direction} correct={prediction.correct} />}
    </g>
  )
}

type LabelProps = { viewBox?: { x: number; y: number; width: number }; prediction: DailyPrediction }

function ForecastLabel({ viewBox, prediction }: LabelProps) {
  if (!viewBox) return null
  const color = COLOR[prediction.direction]
  const center = viewBox.x + viewBox.width / 2
  return (
    <g textAnchor="middle" fill={color}>
      <text x={center} y={viewBox.y + 16} fontSize={11} fill="currentColor" opacity={0.7}>
        Phiên tới
      </text>
      <text x={center} y={viewBox.y + 40} fontSize={22}>
        {ARROW[prediction.direction]}
      </text>
      <text x={center} y={viewBox.y + 58} fontSize={12} fontWeight={600}>
        {DIRECTION_LABEL[prediction.direction]}
      </text>
      <text x={center} y={viewBox.y + 74} fontSize={11}>
        {formatPercent(probabilityOf(prediction), 0)}
      </text>
    </g>
  )
}

function TooltipBody({ row }: { row: Row }) {
  if (row.range === undefined || row.open == null || row.close == null) return null
  const [low, high] = row.range
  const prediction = row.prediction
  return (
    <div className="space-y-1.5 rounded-lg border bg-background px-3 py-2 text-xs shadow-xl">
      <div className="font-medium">{formatDate(row.key)}</div>
      <div className="grid grid-cols-[auto_auto] gap-x-4 tabular-nums">
        <span className="text-muted-foreground">Mở / Đóng</span>
        <span>
          {formatNumber(row.open, 2)} / {formatNumber(row.close, 2)}
          {row.changePct != null && <span className={row.changePct >= 0 ? "ml-1 text-success" : "ml-1 text-destructive"}>({formatPercent(row.changePct, 2)})</span>}
        </span>
        <span className="text-muted-foreground">Thấp / Cao</span>
        <span>
          {formatNumber(low, 2)} / {formatNumber(high, 2)}
        </span>
      </div>
      {prediction && (
        <div className="space-y-0.5 border-t pt-1.5">
          <div style={{ color: COLOR[prediction.direction] }} className="font-medium">
            Dự đoán cho phiên sau: {ARROW[prediction.direction]} {DIRECTION_LABEL[prediction.direction]} ({formatPercent(probabilityOf(prediction), 0)})
          </div>
          <div className="text-muted-foreground tabular-nums">
            điểm {prediction.p_up - prediction.p_down >= 0 ? "+" : ""}
            {formatNumber(prediction.p_up - prediction.p_down, 3)} · giảm {formatPercent(prediction.p_down, 0)} · ngang {formatPercent(prediction.p_flat, 0)} · tăng {formatPercent(prediction.p_up, 0)}
          </div>
          <div className="text-muted-foreground">
            {prediction.correct === null ? "Chưa biết kết quả" : prediction.correct ? "Đã đoán đúng" : "Đã đoán sai"}
            {prediction.source === "oos" ? " · dự đoán ngoài mẫu" : " · dự đoán thực"}
          </div>
        </div>
      )}
    </div>
  )
}

export function CandleChart({ data }: { data: SymbolPredictions }) {
  const byDate = new Map(data.predictions.map((prediction) => [prediction.date, prediction]))
  const candleRows: Row[] = data.candles.map((candle, index) => ({
    key: candle.date,
    range: [candle.low, candle.high],
    open: candle.open,
    close: candle.close,
    changePct: index > 0 ? candle.close / data.candles[index - 1].close - 1 : undefined,
    prediction: byDate.get(candle.date),
    score: byDate.has(candle.date) ? byDate.get(candle.date)!.p_up - byDate.get(candle.date)!.p_down : undefined,
  }))
  const forecast = data.next_session
  const rows = [...candleRows, ...Array.from({ length: forecast ? FUTURE_ROWS : 0 }, (_, index): Row => ({ key: `f${index}` }))]

  const lows = data.candles.map((candle) => candle.low)
  const highs = data.candles.map((candle) => candle.high)
  const span = Math.max(...highs) - Math.min(...lows)
  const priceDigits = span < 3 ? 2 : span < 12 ? 1 : 0
  const domain: [number, number] = [Math.min(...lows) - span * 0.08, Math.max(...highs) + span * 0.04]

  const learned = data.candles.filter((candle) => candle.date > data.last_oos_date && candle.date <= data.trained_until)

  const reach = Math.ceil(Math.max(0.05, ...data.predictions.map((prediction) => Math.abs(prediction.p_up - prediction.p_down))) / 0.05) * 0.05
  const learnedArea = learned.length > 0 && (
    <ReferenceArea ifOverflow="visible" x1={learned[0].date} x2={learned[learned.length - 1].date} fill="currentColor" fillOpacity={0.06} />
  )

  return (
    <div className="flex flex-col gap-1 lg:h-full">
      <ChartContainer config={{}} className="aspect-auto h-[340px] w-full lg:h-auto lg:min-h-0 lg:flex-[3]">
        <ComposedChart data={rows} syncId="candles" margin={{ left: 4, right: 8, top: 8 }} barCategoryGap="10%">
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="key"
          tickLine={false}
          axisLine={false}
          minTickGap={36}
          tickFormatter={(key: string) => (key === "f0" ? "Phiên tới" : key.startsWith("f") ? "" : `${key.slice(8, 10)}/${key.slice(5, 7)}`)}
        />
        <YAxis width={44} tickLine={false} axisLine={false} domain={domain} tickFormatter={(value: number) => formatNumber(value, priceDigits)} allowDataOverflow />
        {learned.length > 0 && (
          <ReferenceArea
            ifOverflow="visible"
            x1={learned[0].date}
            x2={learned[learned.length - 1].date}
            fill="currentColor"
            fillOpacity={0.06}
            label={{ value: "Đã học", position: "insideTop", fontSize: 11, fill: "currentColor", opacity: 0.6 }}
          />
        )}
        {forecast && (
          <ReferenceArea
            ifOverflow="visible"
            x1="f0"
            x2={`f${FUTURE_ROWS - 1}`}
            fill={COLOR[forecast.direction]}
            fillOpacity={0.12}
            label={(props: unknown) => <ForecastLabel {...(props as LabelProps)} prediction={forecast} />}
          />
        )}
        <Tooltip
          cursor={{ fill: "currentColor", fillOpacity: 0.06 }}
          content={({ active, payload }) => (active && payload?.[0] ? <TooltipBody row={payload[0].payload as Row} /> : null)}
        />
        <Bar dataKey="range" shape={(props: unknown) => <Candle {...(props as CandleProps)} />} isAnimationActive={false} />
        </ComposedChart>
      </ChartContainer>
      <div className="pl-12 text-xs text-muted-foreground">Điểm mỗi ngày (xác suất tăng trừ giảm): cột xanh nghiêng về tăng, cột đỏ nghiêng về giảm</div>
      <ChartContainer config={{}} className="aspect-auto h-[110px] w-full lg:h-auto lg:min-h-[70px] lg:flex-1">
        <BarChart data={rows} syncId="candles" margin={{ left: 4, right: 8, top: 8, bottom: 10 }} barCategoryGap="10%">
          <XAxis dataKey="key" hide />
          <YAxis width={44} tickLine={false} axisLine={false} domain={[-reach, reach]} ticks={[-reach, 0, reach]} allowDataOverflow tickFormatter={(value: number) => formatNumber(value, 2)} />
          {learnedArea}
          <ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.4} />
          <Tooltip cursor={{ fill: "currentColor", fillOpacity: 0.06 }} content={() => null} />
          <Bar dataKey="score" isAnimationActive={false}>
            {rows.map((row) => (
              <Cell key={row.key} fill={(row.score ?? 0) >= 0 ? UP_COLOR : DOWN_COLOR} />
            ))}
          </Bar>
        </BarChart>
      </ChartContainer>
    </div>
  )
}
