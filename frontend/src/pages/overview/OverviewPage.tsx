import { CreditCard, DollarSign, TrendingUp, AlertTriangle, RotateCcw } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton, ChartSkeleton } from '@/components/dashboard/LoadingState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getOverview, getRecentActivity, getSystemHealth } from '@/api/overview'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'

export function OverviewPage() {
  const { data: metrics, loading: metricsLoading } = useApi(getOverview)
  const { data: activity, loading: activityLoading } = useApi(getRecentActivity)
  const { data: health, loading: healthLoading } = useApi(getSystemHealth)

  return (
    <PageContainer title="Overview" description="Merchant dashboard — payment recovery overview">
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {metricsLoading ? (
          Array.from({ length: 5 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : metrics ? (
          <>
            <MetricCard
              title="Total Revenue"
              value={formatCurrency(metrics.total_revenue)}
              change={((metrics.total_revenue - metrics.previous_period_revenue) / metrics.previous_period_revenue) * 100}
              changeLabel="vs last 30 days"
              icon={<DollarSign className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue At Risk"
              value={formatCurrency(metrics.revenue_at_risk)}
              description="Failed payments"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Recovered Revenue"
              value={formatCurrency(metrics.recovered_revenue)}
              change={((metrics.recovered_revenue - metrics.previous_period_recovered) / metrics.previous_period_recovered) * 100}
              changeLabel="vs previous period"
              icon={<RotateCcw className="w-4 h-4" />}
            />
            <MetricCard
              title="Failed Payments"
              value={String(metrics.failed_payments)}
              change={((metrics.failed_payments - metrics.previous_period_failed) / metrics.previous_period_failed) * -100}
              changeLabel="vs previous period"
              icon={<CreditCard className="w-4 h-4" />}
            />
            <MetricCard
              title="Recovery Rate"
              value={`${metrics.recovery_rate}%`}
              icon={<TrendingUp className="w-4 h-4" />}
            />
          </>
        ) : null}
      </div>

      {/* Charts + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Charts placeholder */}
        <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
          {metricsLoading ? (
            Array.from({ length: 4 }).map((_, i) => <ChartSkeleton key={i} />)
          ) : (
            <>
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider mb-3">Recovery Rate</p>
                <div className="h-40 flex items-end gap-1">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div key={i} className="flex-1 bg-recovery/30 rounded-t" style={{ height: `${30 + Math.random() * 70}%` }} />
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider mb-3">Failed Payments</p>
                <div className="h-40 flex items-end gap-1">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div key={i} className="flex-1 bg-red-500/30 rounded-t" style={{ height: `${10 + Math.random() * 60}%` }} />
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider mb-3">Recovered Revenue</p>
                <div className="h-40 flex items-end gap-1">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div key={i} className="flex-1 bg-success/30 rounded-t" style={{ height: `${20 + Math.random() * 80}%` }} />
                  ))}
                </div>
              </div>
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider mb-3">Revenue At Risk</p>
                <div className="h-40 flex items-end gap-1">
                  {Array.from({ length: 20 }).map((_, i) => (
                    <div key={i} className="flex-1 bg-warning/30 rounded-t" style={{ height: `${15 + Math.random() * 55}%` }} />
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Recent Activity */}
        <div className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">Recent Activity</p>
          </div>
          <div className="divide-y divide-border">
            {activityLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-4 py-3 space-y-2">
                  <div className="h-3 w-20 bg-secondary animate-pulse rounded" />
                  <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                </div>
              ))
            ) : activity?.map((item) => (
              <div key={item.id} className="px-4 py-3 flex items-center justify-between">
                <div className="min-w-0">
                  <p className="text-[13px] text-foreground font-medium truncate">{item.customer}</p>
                  <p className="text-[11px] text-muted-foreground">{item.id} · {formatCurrency(item.amount)}</p>
                </div>
                <div className="flex flex-col items-end gap-1 ml-3">
                  <StatusBadge status={item.status as never} />
                  <span className="text-[10px] text-muted-foreground">{formatRelativeTime(item.time)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="rounded-lg border border-border bg-card">
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-success" />
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">System Health</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-border">
          {healthLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="px-4 py-3 space-y-2">
                <div className="h-3 w-24 bg-secondary animate-pulse rounded" />
                <div className="h-3 w-16 bg-secondary animate-pulse rounded" />
              </div>
            ))
          ) : health?.map((svc) => (
            <div key={svc.name} className="px-4 py-3">
              <p className="text-[13px] text-foreground font-medium">{svc.name}</p>
              <div className="flex items-center gap-1.5 mt-1">
                <div className="w-1.5 h-1.5 rounded-full bg-success" />
                <span className="text-[11px] text-success capitalize">{svc.status}</span>
                <span className="text-[10px] text-muted-foreground ml-auto">{svc.latency_ms}ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageContainer>
  )
}
