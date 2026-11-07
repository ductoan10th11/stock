import { describe, expect, it } from "vitest"

import { formatDate, formatNumber, formatPercent, formatSignedPercent, formatVnd } from "./format"

describe("format", () => {
  it("shortens VND amounts", () => {
    expect(formatVnd(1.5e9)).toBe("1,50 tỷ")
    expect(formatVnd(2.5e7)).toBe("25,0 triệu")
    expect(formatVnd(-1.5e9)).toBe("-1,50 tỷ")
    expect(formatVnd(950)).toBe("950 đ")
  })

  it("renders missing numbers as a dash", () => {
    expect(formatNumber(null)).toBe("-")
    expect(formatPercent(Number.NaN)).toBe("-")
  })

  it("formats percents with Vietnamese decimals and a sign", () => {
    expect(formatPercent(0.123)).toBe("12,3%")
    expect(formatSignedPercent(0.05)).toBe("+5,00%")
    expect(formatSignedPercent(-0.05)).toBe("-5,00%")
  })

  it("turns ISO dates into dd/mm/yyyy", () => {
    expect(formatDate("2026-11-06")).toBe("06/11/2026")
  })
})
