import { useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { detectSpikes, detectDegradation } from '@/api/monitoring'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'
import { AlertTriangle, TrendingDown, Zap, Shield } from 'lucide-react'

export function SpikeDetectionPage() {
  const [timeWindow, setTimeWindow] = useState(24)
  const [threshold, setThreshold] = useState(2.0)

  const { data: spikeData, loading: spikeLoading } = useApi(
    () => detectSpikes(timeWindow, threshold),
    [timeWindow, threshold]
  )

  const { data: degradationData, loading: degradationLoading } = useApi(
    () => detectDegradation(timeWindow),
    [timeWindow]
  )

  const degradedDimensions = degradationData?.filter(d => d.is_degraded) ?? []

  return (
    <PageContainer
      title="Spike Detection"
      description="Detect anomalies and degradation in payment failure patterns"
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
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        >
          <option value={1.5}>1.5x threshold</option>
          <option value={2.0}>2.0x threshold</option>
          <option value={3.0}>3.0x threshold</option>
          <option value={5.0}>5.0x threshold</option>
        </select>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {spikeLoading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : spikeData ? (
          <>
            <MetricCard
              title="Spikes Detected"
              value={spikeData.spike_count.toString()}
              description={spikeData.spikes_detected ? "Anomalies found" : "No spikes detected"}
              icon={<Zap className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue at Risk"
              value={formatCurrency(spikeData.spikes.reduce((sum, s) => sum + s.revenue_impact, 0))}
              description="From detected spikes"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Degraded Dimensions"
              value={degradedDimensions.length.toString()}
              description="Dimensions with increased failures"
              icon={<TrendingDown className="w-4 h-4" />}
            />
            <MetricCard
              title="Monitoring Status"
              value={spikeData.spikes_detected ? "Alert" : "Normal"}
              description={spikeData.spikes_detected ? "Spikes requiring attention" : "All systems normal"}
              icon={<Shield className="w-4 h-4" />}
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

      {/* Spikes List */}
      <div className="rounded-lg border border-border bg-card mb-6">
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Detected Spikes
            </p>
            {spikeData && (
              <span className="text-[11px] text-muted-foreground">
                {spikeData.period_start} - {spikeData.period_end}
              </span>
            )}
          </div>
        </div>
        <div className="divide-y divide-border">
          {spikeLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="px-4 py-3 space-y-2">
                <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                <div className="h-3 w-48 bg-secondary animate-pulse rounded" />
              </div>
            ))
          ) : spikeData && spikeData.spikes.length > 0 ? (
            spikeData.spikes.map((spike, idx) => (
              <div key={idx} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={spike.severity as never} />
                    <span className="text-[13px] font-medium text-foreground">
                      {spike.dimension}
                    </span>
                  </div>
                  <span className="text-[12px] text-destructive font-mono">
                    {formatCurrency(spike.revenue_impact)}
                  </span>
                </div>
                <p className="text-[12px] text-muted-foreground">{spike.message}</p>
                <div className="flex items-center gap-4 mt-1">
                  <span className="text-[11px] text-muted-foreground">
                    Current: {spike.current_count} failures
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Baseline: {spike.baseline_count} failures
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Threshold: {spike.threshold}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    {formatRelativeTime(spike.detected_at)}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="px-4 py-8 text-center">
              <p className="text-[13px] text-muted-foreground">No spikes detected</p>
            </div>
          )}
        </div>
      </div>

      {/* Degradation Metrics */}
      <div className="rounded-lg border border-border bg-card">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
            Degradation Analysis
          </p>
        </div>
        <div className="divide-y divide-border">
          {degradationLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="px-4 py-3 space-y-2">
                <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                <div className="h-3 w-48 bg-secondary animate-pulse rounded" />
              </div>
            ))
          ) : degradationData && degradationData.length > 0 ? (
            degradationData
              .sort((a, b) => b.change_percentage - a.change_percentage)
              .slice(0, 10)
              .map((metric, idx) => (
                <div key={idx} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[13px] font-medium text-foreground">
                      {metric.dimension}
                    </span>
                    <div className="flex items-center gap-2">
                      {metric.is_degraded && (
                        <StatusBadge status="critical" />
                      )}
                      <span className={`text-[12px] font-mono ${metric.change_percentage > 0 ? 'text-destructive' : 'text-success'}`}>
                        {metric.change_percentage > 0 ? '+' : ''}{metric.change_percentage}%
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-[11px] text-muted-foreground">
                      Current: {metric.current_failure_rate}% failure rate
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Previous: {metric.previous_failure_rate}% failure rate
                    </span>
                    <span className="text-[11px] text-destructive">
                      {formatCurrency(metric.revenue_impact)} impact
                    </span>
                  </div>
                </div>
              ))
          ) : (
            <div className="px-4 py-8 text-center">
              <p className="text-[13px] text-muted-foreground">No degradation detected</p>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
