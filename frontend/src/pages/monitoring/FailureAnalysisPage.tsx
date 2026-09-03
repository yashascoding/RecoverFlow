import { useState } from 'react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getFailureAnalysis } from '@/api/monitoring'
import { formatCurrency } from '@/lib/utils'
import { AlertTriangle, TrendingDown, Layers } from 'lucide-react'

type GroupByOption = 'failure_reason' | 'gateway' | 'bank' | 'region' | 'payment_method'

export function FailureAnalysisPage() {
  const [timeWindow, setTimeWindow] = useState(24)
  const [groupBy, setGroupBy] = useState<GroupByOption>('failure_reason')

  const { data: analysisData, loading, error, refetch } = useApi(
    () => getFailureAnalysis(timeWindow, groupBy),
    [timeWindow, groupBy]
  )

  const columns: Column<{ group_value: string; failure_count: number; revenue_at_risk: number; percentage: number; top_failure_reasons: string[] }>[] = [
    {
      key: 'group_value',
      header: groupBy === 'failure_reason' ? 'Failure Reason' : groupBy.charAt(0).toUpperCase() + groupBy.slice(1),
      render: (row) => (
        <span className="font-medium text-[13px] max-w-[300px] truncate block">
          {row.group_value}
        </span>
      ),
    },
    {
      key: 'failure_count',
      header: 'Failures',
      sortable: true,
      render: (row) => (
        <span className="font-mono text-[13px]">{row.failure_count}</span>
      ),
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
      key: 'percentage',
      header: 'Percentage',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground text-[13px]">{row.percentage}%</span>
      ),
    },
    {
      key: 'top_failure_reasons',
      header: 'Top Reasons',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.top_failure_reasons.slice(0, 2).map((reason, idx) => (
            <StatusBadge key={idx} status={reason.substring(0, 20)} />
          ))}
        </div>
      ),
    },
  ]

  return (
    <PageContainer
      title="Failure Analysis"
      description="Analyze payment failures by different dimensions"
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
          value={groupBy}
          onChange={(e) => setGroupBy(e.target.value as GroupByOption)}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        >
          <option value="failure_reason">By Failure Reason</option>
          <option value="gateway">By Gateway</option>
          <option value="bank">By Bank</option>
          <option value="region">By Region</option>
          <option value="payment_method">By Payment Method</option>
        </select>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : analysisData ? (
          <>
            <MetricCard
              title="Total Failures"
              value={analysisData.total_failures.toString()}
              description="Failed transactions"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue at Risk"
              value={formatCurrency(analysisData.revenue_at_risk)}
              description="Total amount at risk"
              icon={<TrendingDown className="w-4 h-4" />}
            />
            <MetricCard
              title="Failure Groups"
              value={analysisData.groups.length.toString()}
              description={`Grouped by ${groupBy.replace('_', ' ')}`}
              icon={<Layers className="w-4 h-4" />}
            />
          </>
        ) : (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-4 flex flex-col items-center justify-center h-[100px]">
              <p className="text-[11px] text-muted-foreground">No data yet</p>
            </div>
          ))
        )}
      </div>

      {/* Analysis Table */}
      {loading ? (
        <div className="rounded-lg border border-border bg-card p-6">
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-secondary animate-pulse rounded" />
            ))}
          </div>
        </div>
      ) : error ? (
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          <p className="text-destructive text-[13px]">{error}</p>
          <button
            onClick={refetch}
            className="mt-2 text-[12px] text-recovery hover:underline"
          >
            Retry
          </button>
        </div>
      ) : analysisData && analysisData.groups.length > 0 ? (
        <div className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Failures by {groupBy.replace('_', ' ')}
            </p>
          </div>
          <DataTable
            columns={columns}
            data={analysisData.groups}
            pageSize={10}
          />
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          <p className="text-[13px] text-muted-foreground">No failure data available</p>
        </div>
      )}
    </PageContainer>
  )
}
