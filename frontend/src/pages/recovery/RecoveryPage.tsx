import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { MetricCardSkeleton, TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { useApi } from '@/hooks/useApi'
import { getRecoveryAttempts } from '@/api/recovery'
import { formatCurrency, formatRelativeTime, truncateId } from '@/lib/utils'
import type { RecoveryAttempt } from '@/types'
import { RotateCcw, CheckCircle, Mail, Clock } from 'lucide-react'

export function RecoveryPage() {
  const { data: attempts, loading, error, refetch } = useApi(getRecoveryAttempts)

  const perf = {
    total: attempts?.length ?? 0,
    successful: attempts?.filter(a => a.status === 'recovered').length ?? 0,
    revenue: attempts?.filter(a => a.recovery_amount).reduce((s, a) => s + (a.recovery_amount ?? 0), 0) ?? 0,
    rate: attempts ? ((attempts.filter(a => a.status === 'recovered').length / attempts.length) * 100) : 0,
  }

  const columns: Column<RecoveryAttempt>[] = [
    {
      key: 'payment_order_id',
      header: 'Payment',
      render: (row) => <span className="font-mono text-[12px]">{truncateId(row.payment_order_id, 12)}</span>,
    },
    {
      key: 'customer_name',
      header: 'Customer',
      sortable: true,
      render: (row) => <span className="font-medium">{row.customer_name}</span>,
    },
    {
      key: 'original_amount',
      header: 'Original Amount',
      sortable: true,
      render: (row) => <span className="font-mono">{formatCurrency(row.original_amount)}</span>,
    },
    {
      key: 'recovery_amount',
      header: 'Recovered',
      sortable: true,
      render: (row) => row.recovery_amount ? <span className="font-mono text-success">{formatCurrency(row.recovery_amount)}</span> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: 'recovery_time',
      header: 'Recovery Time',
      render: (row) => row.recovery_time ? <span className="text-foreground">{row.recovery_time}</span> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: 'channel',
      header: 'Channel',
      render: (row) => <span className="capitalize">{row.channel}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => <span className="text-muted-foreground whitespace-nowrap">{formatRelativeTime(row.created_at)}</span>,
    },
  ]

  return (
    <PageContainer title="Recovery" description="Payment recovery attempts and performance metrics">
      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : (
          <>
            <MetricCard title="Total Attempts" value={String(perf.total)} icon={<RotateCcw className="w-4 h-4" />} />
            <MetricCard title="Successful" value={String(perf.successful)} icon={<CheckCircle className="w-4 h-4" />} />
            <MetricCard title="Recovered Revenue" value={formatCurrency(perf.revenue)} icon={<Mail className="w-4 h-4" />} />
            <MetricCard title="Recovery Rate" value={`${perf.rate.toFixed(1)}%`} icon={<Clock className="w-4 h-4" />} />
          </>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <TableSkeleton rows={8} columns={8} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (attempts?.length ?? 0) === 0 ? (
        <EmptyState
          title="No recovery attempts yet"
          description="Recovery attempts will appear here when failed payments are processed"
          icon={<RotateCcw className="w-8 h-8" />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={attempts ?? []}
          pageSize={10}
        />
      )}
    </PageContainer>
  )
}
