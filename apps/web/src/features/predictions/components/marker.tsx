import { DOWN_COLOR, FLAT_COLOR, UP_COLOR } from "@/lib/colors"

import type { Direction } from "../types"

const COLOR: Record<Direction, string> = { up: UP_COLOR, down: DOWN_COLOR, flat: FLAT_COLOR }

type Props = { cx: number; cy: number; direction: Direction; correct: boolean | null }

/** Solid = the prediction came true, hollow = it did not, faded = the outcome is not known yet. */
export function Marker({ cx, cy, direction, correct }: Props) {
  const color = COLOR[direction]
  const common = {
    fill: correct === false ? "transparent" : color,
    fillOpacity: correct === null ? 0.55 : 1,
    stroke: color,
    strokeWidth: 1.5,
  }
  if (direction === "flat") return <circle cx={cx} cy={cy} r={3.5} {...common} />
  const tip = direction === "up" ? -5 : 5
  return <polygon points={`${cx},${cy + tip} ${cx - 4.5},${cy - tip * 0.6} ${cx + 4.5},${cy - tip * 0.6}`} {...common} />
}
