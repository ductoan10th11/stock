import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function ListSkeleton() {
  return (
    <div className="space-y-2 px-3 py-2" aria-busy="true" aria-label="Đang tải danh sách mã">
      {Array.from({ length: 19 }, (_, index) => (
        <Skeleton key={index} className="h-6 w-full" />
      ))}
    </div>
  )
}

/** Same shape as the loaded panel; the symbol name is already known from the click. */
export function PanelSkeleton({ symbol }: { symbol: string | undefined }) {
  return (
    <>
      <Card className="shrink-0 gap-0 py-3" aria-busy="true" aria-label={`Đang tải dự đoán ${symbol ?? ""}`}>
        <CardContent className="grid items-center gap-x-8 gap-y-3 md:grid-cols-[auto_minmax(0,1fr)_minmax(0,1.3fr)]">
          <div className="space-y-2">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-8 w-28" />
            <Skeleton className="h-3 w-20" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-2 w-full" />
            <Skeleton className="h-2 w-full" />
            <Skeleton className="h-2 w-full" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-3 w-full" />
          </div>
        </CardContent>
      </Card>
      <Card className="min-h-0 gap-2 py-3 lg:flex-1">
        <CardHeader className="shrink-0">
          <CardTitle>{symbol ? `${symbol}: nến ngày và xu hướng dự đoán` : "Đang tải..."}</CardTitle>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-2">
          <Skeleton className="h-[340px] w-full lg:h-auto lg:min-h-0 lg:flex-[3]" />
          <Skeleton className="h-[110px] w-full lg:h-auto lg:min-h-[70px] lg:flex-1" />
          <Skeleton className="h-3 w-3/4 shrink-0" />
        </CardContent>
      </Card>
    </>
  )
}
