import { Area, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts"

import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart"
import { formatDate } from "@/lib/format"

export type LineSeries = {
  key: string
  label: string
  color: string
  dash: "solid" | "dash" | "dot"
  values: (number | null)[]
}

const DASH = { solid: undefined, dash: "6 4", dot: "2 3" } as const

type Props = {
  dates: string[]
  series: LineSeries[]
  formatValue: (value: number) => string
  log?: boolean
  height?: number
  fill?: boolean
  area?: boolean
}

export function TimeLineChart({ dates, series, formatValue, log = false, height = 360, fill = false, area = false }: Props) {
  const spanDays = (Date.parse(dates[dates.length - 1]) - Date.parse(dates[0])) / 864e5
  const tick = (date: string) => (spanDays > 500 ? `${date.slice(5, 7)}/${date.slice(0, 4)}` : `${date.slice(8, 10)}/${date.slice(5, 7)}`)
  const data = dates.map((date, index) => ({ date, ...Object.fromEntries(series.map((line) => [line.key, line.values[index]])) }))
  const config: ChartConfig = Object.fromEntries(series.map((line) => [line.key, { label: line.label, color: line.color }]))
  return (
    <ChartContainer config={config} className={fill ? "aspect-auto h-full w-full" : "w-full"} style={fill ? undefined : { height }}>
      <ComposedChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <defs>
          {series.map((line) => (
            <linearGradient key={line.key} id={`area-${line.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={line.color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={line.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid vertical={false} strokeDasharray="3 6" strokeOpacity={0.35} />
        <XAxis dataKey="date" tickFormatter={tick} minTickGap={64} tickLine={false} axisLine={false} />
        <YAxis
          width={56}
          tickLine={false}
          axisLine={false}
          scale={log ? "log" : "linear"}
          domain={["auto", "auto"]}
          tickFormatter={(value: number) => formatValue(value)}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => formatDate(String(label))}
              formatter={(value, name, item) => (
                <>
                  <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: item.color }} />
                  <span className="text-muted-foreground">{config[String(name)]?.label ?? name}</span>
                  <span className="ml-auto pl-4 font-mono font-medium tabular-nums">{formatValue(Number(value))}</span>
                </>
              )}
            />
          }
        />
        <ChartLegend content={<ChartLegendContent className="flex-wrap gap-x-3 gap-y-0.5 text-xs [&>div]:whitespace-nowrap" />} />
        {area && (
          <Area dataKey={series[0].key} type="monotone" stroke="none" fill={`url(#area-${series[0].key})`} isAnimationActive={false} connectNulls legendType="none" tooltipType="none" />
        )}
        {series.map((line, index) => (
          <Line
            key={line.key}
            dataKey={line.key}
            type={area ? "monotone" : "linear"}
            stroke={line.color}
            strokeWidth={area && index > 0 ? 1.5 : 2}
            strokeOpacity={area && index > 0 ? 0.75 : 1}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={DASH[line.dash]}
            dot={false}
            activeDot={{ r: 3.5, strokeWidth: 0 }}
            isAnimationActive={false}
            connectNulls
          />
        ))}
      </ComposedChart>
    </ChartContainer>
  )
}
