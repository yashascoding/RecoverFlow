import { CreditCard, DollarSign, TrendingUp, AlertTriangle, RotateCcw, Eye, Brain, Shield, Mail, CheckCircle2, Zap } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getOverview, getRecentActivity, getSystemHealth } from '@/api/overview'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'

function HowItWorksBlock() {
  const steps = [
    { icon: AlertTriangle, label: 'Detect', desc: 'Payment failure webhook arrives from Razorpay' },
    { icon: Eye, label: 'Observe', desc: 'Revenue Sentinel detects the failure event' },
    { icon: Brain, label: 'Investigate', desc: 'AI agent analyzes payment, customer, and context' },
    { icon: Shield, label: 'Policy Check', desc: 'Deterministic firewall validates the action' },
    { icon: Mail, label: 'Recover', desc: 'Send secure payment link to customer' },
    { icon: CheckCircle2, label: 'Verify', desc: 'Confirm successful payment and measure revenue' },
  ]

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-md bg-blue-500/10 flex items-center justify-center">
          <Zap className="w-4 h-4 text-blue-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">How RecoverFlow Works</h3>
          <p className="text-[12px] text-muted-foreground">End-to-end autonomous payment recovery pipeline</p>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {steps.map((step, i) => (
          <div key={i} className="relative">
            <div className="rounded-md bg-secondary/50 border border-border p-3 h-full">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono text-muted-foreground">0{i + 1}</span>
                <step.icon className="w-3.5 h-3.5 text-blue-400" />
              </div>
              <p className="text-[12px] font-medium text-foreground">{step.label}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{step.desc}</p>
            </div>
            {i < steps.length - 1 && (
              <div className="hidden lg:block absolute top-1/2 -right-1.5 w-3 h-px bg-border" />
            )}
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-border">
        <p className="text-[12px] text-muted-foreground">
          Connect your Razorpay webhooks and configure policies to start recovering failed payments automatically.
        </p>
      </div>
    </div>
  )
}

export function OverviewPage() {
  const { data: metrics, loading: metricsLoading } = useApi(getOverview)
  const { data: activity, loading: activityLoading } = useApi(getRecentActivity)
  const { data: health, loading: healthLoading } = useApi(getSystemHealth)

  const hasData = metrics && (metrics.total_payments > 0 || metrics.failed_payments > 0)

  return (
    <PageContainer title="Overview" description="Merchant dashboard — payment recovery overview">
      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricsLoading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : hasData ? (
          <>
            <MetricCard
              title="Total Revenue"
              value={formatCurrency(metrics.total_revenue)}
              change={metrics.previous_period_revenue > 0 ? ((metrics.total_revenue - metrics.previous_period_revenue) / metrics.previous_period_revenue) * 100 : undefined}
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
              change={metrics.previous_period_recovered > 0 ? ((metrics.recovered_revenue - metrics.previous_period_recovered) / metrics.previous_period_recovered) * 100 : undefined}
              changeLabel="vs previous period"
              icon={<RotateCcw className="w-4 h-4" />}
            />
            <MetricCard
              title="Recovery Rate"
              value={`${metrics.recovery_rate}%`}
              description={`${metrics.failed_payments} failed payments`}
              icon={<TrendingUp className="w-4 h-4" />}
            />
          </>
        ) : (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-4 flex flex-col items-center justify-center h-[100px]">
              <p className="text-[11px] text-muted-foreground">No data yet</p>
            </div>
          ))
        )}
      </div>

      {/* Activity + How It Works (when no data) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Activity — wider */}
        <div className="lg:col-span-2 rounded-lg border border-border bg-card">
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
            ) : activity && activity.length > 0 ? (
              activity.slice(0, 6).map((item) => (
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
              ))
            ) : (
              <div className="px-4 py-8">
                <EmptyState
                  title="No activity yet"
                  description="Recent payment activity will appear here"
                />
              </div>
            )}
          </div>
        </div>

        {/* System Health — right column */}
        <div className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${health && health.length > 0 ? 'bg-success' : 'bg-muted-foreground'}`} />
              <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">System Health</p>
            </div>
          </div>
          <div className="divide-y divide-border">
            {healthLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="px-4 py-3 space-y-2">
                  <div className="h-3 w-24 bg-secondary animate-pulse rounded" />
                  <div className="h-3 w-16 bg-secondary animate-pulse rounded" />
                </div>
              ))
            ) : health && health.length > 0 ? (
              health.map((svc) => (
                <div key={svc.name} className="px-4 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-[13px] text-foreground font-medium">{svc.name}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-success" />
                      <span className="text-[11px] text-success capitalize">{svc.status}</span>
                    </div>
                  </div>
                  <span className="text-[11px] text-muted-foreground font-mono">{svc.latency_ms}ms</span>
                </div>
              ))
            ) : (
              <div className="px-4 py-6">
                <p className="text-[12px] text-muted-foreground text-center">System health status unavailable</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* How It Works Block - only when no data */}
      {!metricsLoading && !hasData && <HowItWorksBlock />}
    </PageContainer>
  )
}
