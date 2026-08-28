import { PageContainer } from '@/components/layout/PageContainer'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { useApi } from '@/hooks/useApi'
import { getAuditEvents } from '@/api/audit'
import { formatDateTime, truncateId } from '@/lib/utils'
import type { AuditEvent } from '@/types'
import { useState } from 'react'

export function AuditPage() {
  const { data: events, loading, error, refetch } = useApi(getAuditEvents)
  const [search, setSearch] = useState('')
  const [resultFilter, setResultFilter] = useState<string>('all')

  const filtered = events?.filter(e => {
    const matchSearch = !search ||
      e.action.toLowerCase().includes(search.toLowerCase()) ||
      e.actor.toLowerCase().includes(search.toLowerCase()) ||
      e.description.toLowerCase().includes(search.toLowerCase())
    const matchResult = resultFilter === 'all' || e.result === resultFilter
    return matchSearch && matchResult
  }) ?? []

  const columns: Column<AuditEvent>[] = [
    {
      key: 'timestamp',
      header: 'Time',
      sortable: true,
      render: (row) => <span className="font-mono text-[12px] text-muted-foreground whitespace-nowrap">{formatDateTime(row.timestamp)}</span>,
    },
    {
      key: 'action',
      header: 'Action',
      sortable: true,
      render: (row) => <span className="font-mono text-[12px] font-medium">{row.action}</span>,
    },
    {
      key: 'actor',
      header: 'Actor',
      sortable: true,
      render: (row) => <StatusBadge status={row.actor.toLowerCase() as never} />,
    },
    {
      key: 'description',
      header: 'Description',
      render: (row) => <span className="text-muted-foreground max-w-[280px] truncate block">{row.description}</span>,
    },
    {
      key: 'policy_name',
      header: 'Policy',
      render: (row) => row.policy_name ? <span className="font-mono text-[12px]">{row.policy_name}</span> : <span className="text-muted-foreground">—</span>,
    },
    {
      key: 'result',
      header: 'Result',
      sortable: true,
      render: (row) => <StatusBadge status={row.result} />,
    },
    {
      key: 'resource_id',
      header: 'Resource',
      render: (row) => <span className="font-mono text-[11px] text-muted-foreground">{truncateId(row.resource_id, 10)}</span>,
    },
  ]

  return (
    <PageContainer title="Audit Log" description="Complete audit trail of all recovery actions and decisions">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search audit events..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-64 rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <select
          value={resultFilter}
          onChange={(e) => setResultFilter(e.target.value)}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="all">All Results</option>
          <option value="success">Success</option>
          <option value="allowed">Allowed</option>
          <option value="blocked">Blocked</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {loading ? (
        <TableSkeleton rows={10} columns={7} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          pageSize={15}
        />
      )}
    </PageContainer>
  )
}
