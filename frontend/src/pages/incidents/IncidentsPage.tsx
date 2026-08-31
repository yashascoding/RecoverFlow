import { useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { useApi } from '@/hooks/useApi'
import { getIncidents } from '@/api/recovery'
import { formatRelativeTime, truncateId } from '@/lib/utils'
import type { Incident } from '@/types'
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'

export function IncidentsPage() {
  const navigate = useNavigate()
  const { data: incidents, loading, error, refetch } = useApi(getIncidents)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filtered = incidents?.filter(i => {
    const matchSearch = !search ||
      i.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      i.payment_order_id.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || i.status === statusFilter
    return matchSearch && matchStatus
  }) ?? []

  const columns: Column<Incident>[] = [
    {
      key: 'id',
      header: 'Incident ID',
      render: (row) => <span className="font-mono text-[12px]">{truncateId(row.id, 10)}</span>,
    },
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
      key: 'failure_reason',
      header: 'Failure Reason',
      render: (row) => <span className="text-muted-foreground max-w-[200px] truncate block">{row.failure_reason}</span>,
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
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => <span className="text-muted-foreground whitespace-nowrap">{formatRelativeTime(row.created_at)}</span>,
    },
    {
      key: 'recovery_state',
      header: 'Recovery',
      render: (row) => row.recovery_state ? <StatusBadge status={row.recovery_state as never} /> : <span className="text-muted-foreground">—</span>,
    },
  ]

  return (
    <PageContainer title="Incidents" description="Failed payments requiring investigation and recovery">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search incidents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-64 rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="investigating">Investigating</option>
          <option value="recovery_pending">Recovery Pending</option>
          <option value="recovered">Recovered</option>
          <option value="escalated">Escalated</option>
        </select>
      </div>

      {loading ? (
        <TableSkeleton rows={8} columns={8} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No incidents yet"
          description="Incidents will be created when payment failures are detected"
          icon={<AlertTriangle className="w-8 h-8" />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          pageSize={10}
          onRowClick={(row) => navigate(`/incidents/${row.id}`)}
        />
      )}
    </PageContainer>
  )
}
