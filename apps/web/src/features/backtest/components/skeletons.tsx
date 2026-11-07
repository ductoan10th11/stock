import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function ResultsSkeleton() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3" aria-busy="true" aria-label="Đang chạy backtest">
      <div className="grid shrink-0 grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-3">
        {Array.from({ length: 3 }, (_, index) => (
          <Card key={index} className="gap-0 py-3">
            <CardContent className="space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-7 w-28" />
              <Skeleton className="h-3 w-56" />
            </CardContent>
          </Card>
        ))}
      </div>
      <Skeleton className="h-[260px] w-full lg:h-auto lg:flex-[3]" />
      <Skeleton className="h-[180px] w-full lg:h-auto lg:flex-[2]" />
    </div>
  )
}
