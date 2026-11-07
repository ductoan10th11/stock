const locale = "vi-VN"

const decimal = (digits: number) =>
  new Intl.NumberFormat(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits })

export function formatNumber(value: number | null | undefined, digits = 0): string {
  return value == null || Number.isNaN(value) ? "-" : decimal(digits).format(value)
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  return value == null || Number.isNaN(value) ? "-" : `${decimal(digits).format(value * 100)}%`
}

export function formatSignedPercent(value: number, digits = 2): string {
  return `${value >= 0 ? "+" : ""}${formatPercent(value, digits)}`
}

export function formatVnd(value: number): string {
  const abs = Math.abs(value)
  if (abs >= 1e9) return `${decimal(2).format(value / 1e9)} tỷ`
  if (abs >= 1e6) return `${decimal(1).format(value / 1e6)} triệu`
  return `${decimal(0).format(value)} đ`
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-")
  return `${day}/${month}/${year}`
}

export const formatMultiple = (value: number, digits = 2) => `${decimal(digits).format(value)}×`
