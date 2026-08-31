import { cn } from '@/lib/utils'

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-secondary/70', className)} />
}

export function MetricCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-7 w-24" />
        </div>
        <Skeleton className="h-9 w-9 rounded-md" />
      </div>
      <div className="mt-3">
        <Skeleton className="h-3 w-28" />
      </div>
    </div>
  )
}

export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="p-4 border-b border-border">
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            {Array.from({ length: columns }).map((_, j) => (
              <Skeleton key={j} className="h-3.5 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <Skeleton className="h-3.5 w-24 mb-4" />
      <Skeleton className="h-44 w-full rounded-md" />
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="p-6 max-w-[1400px] space-y-6">
      <div>
        <Skeleton className="h-5 w-32 mb-1" />
        <Skeleton className="h-3.5 w-64" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    </div>
  )
}
