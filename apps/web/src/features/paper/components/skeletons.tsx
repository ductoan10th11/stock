import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function OverviewSkeleton() {
  return (
    <div className="grid gap-4 lg:h-full lg:grid-cols-[minmax(0,1fr)_22rem]" aria-busy="true" aria-label="Đang tải tổng quan">
      <Card className="min-h-0 gap-3 py-4">
        <CardContent className="flex min-h-0 flex-1 flex-col gap-3">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-4 w-56" />
          <Skeleton className="h-[260px] w-full lg:h-auto lg:flex-1" />
        </CardContent>
      </Card>
      <div className="flex min-h-0 flex-col gap-4">
        <Card className="gap-3 py-4">
          <CardHeader className="gap-2">
            <Skeleton className="h-5 w-24" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
        </Card>
        <Card className="gap-3 py-4 lg:flex-1">
          <CardHeader className="gap-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-4 w-56" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export function TableSkeleton() {
  return (
    <Card aria-busy="true" aria-label="Đang tải">
      <CardContent className="space-y-3">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-8 w-full" />
        ))}
      </CardContent>
    </Card>
  )
}
