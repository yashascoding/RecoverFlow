import { useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { useApi } from '@/hooks/useApi'
import { getTransactionMonitoring } from '@/api/monitoring'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'
import { TrendingUp, TrendingDown, AlertTriangle, RotateCcw, Activity } from 'lucide-react'

export function TransactionMonitoringPage() {
  const [timeWindow, setTimeWindow] = useState(24)
  const [granularity, setGranularity] = useState('hourly')

  const { data: monitoringData, loading } = useApi(
    () => getTransactionMonitoring(timeWindow, granularity),
    [timeWindow, granularity]
  )

  const metrics = monitoringData?.metrics
  const timeSeries = monitoringData?.time_series ?? []

  return (
    <PageContainer
      title="Transaction Monitoring"
      description="Real-time transaction health metrics and failure analysis"
    >
      {/* Controls */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={timeWindow}
          onChange={(e) => setTimeWindow(Number(e.target.value))}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        >
          <option value={1}>Last 1 hour</option>
          <option value={6}>Last 6 hours</option>
          <option value={24}>Last 24 hours</option>
          <option value={72}>Last 3 days</option>
          <option value={168}>Last 7 days</option>
        </select>
        <select
          value={granularity}
          onChange={(e) => setGranularity(e.target.value)}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        >
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
        </select>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : metrics ? (
          <>
            <MetricCard
              title="Success Rate"
              value={`${metrics.success_rate}%`}
              description={`${metrics.successful_transactions} of ${metrics.total_transactions} transactions`}
              icon={<TrendingUp className="w-4 h-4" />}
            />
            <MetricCard
              title="Failure Rate"
              value={`${metrics.failure_rate}%`}
              description={`${metrics.failed_transactions} failed transactions`}
              icon={<TrendingDown className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue at Risk"
              value={formatCurrency(metrics.revenue_at_risk)}
              description="From failed payments"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Recovered Revenue"
              value={formatCurrency(metrics.recovered_revenue)}
              description={`${metrics.recovery_rate}% recovery rate`}
              icon={<RotateCcw className="w-4 h-4" />}
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

      {/* Time Series Chart Placeholder */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-md bg-blue-500/10 flex items-center justify-center">
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Transaction Trends</h3>
            <p className="text-[12px] text-muted-foreground">
              {timeSeries.length} data points over the selected period
            </p>
          </div>
        </div>

        {timeSeries.length > 0 ? (
          <div className="space-y-2">
            {timeSeries.slice(-10).map((point, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-[12px] text-muted-foreground">
                  {formatRelativeTime(point.timestamp)}
                </span>
                <div className="flex items-center gap-4">
                  <span className="text-[12px] text-success">
                    {point.success_rate.toFixed(1)}% success
                  </span>
                  <span className="text-[12px] text-destructive">
                    {point.failure_rate.toFixed(1)}% failure
                  </span>
                  <span className="text-[12px] text-muted-foreground">
                    {formatCurrency(point.revenue_at_risk)} at risk
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-[12px] text-muted-foreground">No time series data available</p>
          </div>
        )}
      </div>
    </PageContainer>
  )
}
