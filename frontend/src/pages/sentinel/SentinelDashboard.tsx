import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { useApi } from '@/hooks/useApi'
import { getIncidentStats, getIncidents } from '@/api/incidents'
import { getAlerts } from '@/api/alerts'
import { getSentinelStatus, runSentinelCheck } from '@/api/sentinel'
import { getTransactionSummary, getFailureSummary } from '@/api/monitoring'
import { formatCurrency, formatRelativeTime } from '@/lib/utils'
import {
  AlertTriangle,
  Activity,
  Shield,
  Zap,
  TrendingDown,
  RefreshCw,
  Eye,
  Brain,
} from 'lucide-react'

export function SentinelDashboard() {
  const navigate = useNavigate()
  const [sentinelRunning, setSentinelRunning] = useState(false)
  const [lastSentinelRun, setLastSentinelRun] = useState<string | null>(null)

  const { data: incidentStats, loading: statsLoading } = useApi(getIncidentStats)
  const { data: incidents, loading: incidentsLoading } = useApi(() => getIncidents(undefined, undefined, 1, 10))
  const { data: alerts } = useApi(() => getAlerts('active', undefined, 1, 10))
  const { data: sentinelStatus, loading: sentinelLoading, refetch: refetchSentinel } = useApi(getSentinelStatus)
  const { data: transactionSummary, loading: transactionLoading } = useApi(() => getTransactionSummary(24))
  const { data: failureSummary, loading: failureLoading } = useApi(() => getFailureSummary(24))

  const handleRunSentinel = async () => {
    setSentinelRunning(true)
    try {
      await runSentinelCheck()
      setLastSentinelRun(new Date().toISOString())
      await refetchSentinel()
    } catch (error) {
      console.error('Sentinel run failed:', error)
    } finally {
      setSentinelRunning(false)
    }
  }

  const incidentColumns: Column<{ id: string; title: string; severity: string; status: string; revenue_at_risk: number; created_at: string }>[] = [
    {
      key: 'id',
      header: 'ID',
      render: (row) => <span className="font-mono text-[12px] text-muted-foreground">{row.id.slice(0, 8)}</span>,
    },
    {
      key: 'title',
      header: 'Title',
      render: (row) => <span className="font-medium text-[13px]">{row.title}</span>,
    },
    {
      key: 'severity',
      header: 'Severity',
      sortable: true,
      render: (row) => <StatusBadge status={row.severity} />,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'revenue_at_risk',
      header: 'Revenue at Risk',
      sortable: true,
      render: (row) => (
        <span className="text-destructive font-mono text-[13px]">
          {formatCurrency(row.revenue_at_risk)}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => <span className="text-muted-foreground text-[12px]">{formatRelativeTime(row.created_at)}</span>,
    },
  ]

  return (
    <PageContainer
      title="Sentinel Dashboard"
      description="Monitor payment health, incidents, and automated investigations"
    >
      {/* Sentinel Control */}
      <div className="rounded-lg border border-border bg-card p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md bg-recovery/10 flex items-center justify-center">
              <Eye className="w-5 h-5 text-recovery" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Revenue Sentinel</h3>
              <p className="text-[12px] text-muted-foreground">
                {sentinelLoading ? 'Loading...' : sentinelStatus ? `Active · ${sentinelStatus.active_alerts} alerts configured` : 'Ready to monitor'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastSentinelRun && (
              <span className="text-[11px] text-muted-foreground">
                Last run: {formatRelativeTime(lastSentinelRun)}
              </span>
            )}
            <button
              onClick={handleRunSentinel}
              disabled={sentinelRunning}
              className="flex items-center gap-2 px-4 py-2 rounded-md bg-recovery text-white text-[13px] font-medium hover:bg-recovery/90 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${sentinelRunning ? 'animate-spin' : ''}`} />
              {sentinelRunning ? 'Running...' : 'Run Sentinel Check'}
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statsLoading || transactionLoading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : (
          <>
            <MetricCard
              title="Success Rate"
              value={transactionSummary ? `${transactionSummary.success_rate}%` : '0%'}
              description="Transaction success rate"
              icon={<Activity className="w-4 h-4" />}
            />
            <MetricCard
              title="Open Incidents"
              value={incidentStats ? incidentStats.open_incidents.toString() : '0'}
              description="Requiring attention"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue at Risk"
              value={incidentStats ? formatCurrency(incidentStats.total_revenue_at_risk) : '₹0'}
              description="From active incidents"
              icon={<TrendingDown className="w-4 h-4" />}
            />
            <MetricCard
              title="Active Alerts"
              value={alerts ? alerts.total.toString() : '0'}
              description="Monitoring thresholds"
              icon={<Shield className="w-4 h-4" />}
            />
          </>
        )}
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Incidents Table */}
        <div className="lg:col-span-2 rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center justify-between">
              <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
                Recent Incidents
              </p>
              <button
                onClick={() => navigate('/incidents')}
                className="text-[12px] text-recovery hover:underline"
              >
                View All
              </button>
            </div>
          </div>
          <div className="p-4">
            {incidentsLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-12 bg-secondary animate-pulse rounded" />
                ))}
              </div>
            ) : incidents && incidents.items.length > 0 ? (
              <DataTable
                columns={incidentColumns}
                data={incidents.items.slice(0, 5)}
                pageSize={5}
                onRowClick={(row) => navigate(`/incidents/${row.id}`)}
              />
            ) : (
              <div className="text-center py-8">
                <p className="text-[13px] text-muted-foreground">No incidents yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Sentinel Status */}
          <div className="rounded-lg border border-border bg-card">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
                Sentinel Status
              </p>
            </div>
            <div className="p-4 space-y-3">
              {sentinelLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="h-6 bg-secondary animate-pulse rounded" />
                  ))}
                </div>
              ) : sentinelStatus ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-foreground">Status</span>
                    <StatusBadge status={sentinelStatus.status} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-foreground">Active Alerts</span>
                    <span className="text-[13px] font-mono">{sentinelStatus.active_alerts}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-foreground">Open Incidents</span>
                    <span className="text-[13px] font-mono">{sentinelStatus.open_incidents}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-foreground">Investigating</span>
                    <span className="text-[13px] font-mono">{sentinelStatus.investigating_incidents}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] text-foreground">Revenue at Risk</span>
                    <span className="text-[13px] font-mono text-destructive">
                      {formatCurrency(sentinelStatus.total_revenue_at_risk)}
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-[12px] text-muted-foreground text-center">No status available</p>
              )}
            </div>
          </div>

          {/* Failure Summary */}
          <div className="rounded-lg border border-border bg-card">
            <div className="px-4 py-3 border-b border-border">
              <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
                Top Failure Reasons
              </p>
            </div>
            <div className="divide-y divide-border">
              {failureLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                    <div className="h-3 w-20 bg-secondary animate-pulse rounded" />
                  </div>
                ))
              ) : failureSummary && failureSummary.by_failure_reason.length > 0 ? (
                failureSummary.by_failure_reason.slice(0, 5).map((reason, idx) => (
                  <div key={idx} className="px-4 py-3">
                    <p className="text-[13px] text-foreground font-medium truncate">
                      {reason.name}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[11px] text-muted-foreground">
                        {reason.count} failures
                      </span>
                      <span className="text-[11px] text-destructive">
                        {formatCurrency(reason.revenue_at_risk)}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-4 py-8 text-center">
                  <p className="text-[12px] text-muted-foreground">No failure data</p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="rounded-lg border border-border bg-card p-4">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Quick Actions
            </p>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/monitoring')}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/50 text-[13px] text-foreground hover:bg-secondary transition-colors"
              >
                <Activity className="w-4 h-4" />
                Transaction Monitoring
              </button>
              <button
                onClick={() => navigate('/monitoring/failures')}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/50 text-[13px] text-foreground hover:bg-secondary transition-colors"
              >
                <TrendingDown className="w-4 h-4" />
                Failure Analysis
              </button>
              <button
                onClick={() => navigate('/monitoring/spikes')}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-secondary/50 text-[13px] text-foreground hover:bg-secondary transition-colors"
              >
                <Zap className="w-4 h-4" />
                Spike Detection
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="rounded-lg border border-border bg-card p-6 mt-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-md bg-blue-500/10 flex items-center justify-center">
            <Brain className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">How Sentinel Works</h3>
            <p className="text-[12px] text-muted-foreground">Automated monitoring and investigation pipeline</p>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { step: '01', label: 'Monitor', desc: 'Continuously track transaction metrics' },
            { step: '02', label: 'Detect', desc: 'Identify spikes and degradation patterns' },
            { step: '03', label: 'Alert', desc: 'Trigger alerts when thresholds exceeded' },
            { step: '04', label: 'Investigate', desc: 'AI agent analyzes root causes automatically' },
          ].map((item, idx) => (
            <div key={idx} className="rounded-md bg-secondary/50 border border-border p-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono text-muted-foreground">{item.step}</span>
              </div>
              <p className="text-[12px] font-medium text-foreground">{item.label}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </PageContainer>
  )
}
