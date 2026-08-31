import { useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { useApi } from '@/hooks/useApi'
import { getAgentRuns } from '@/api/agentRuns'
import { formatRelativeTime, truncateId } from '@/lib/utils'
import type { AgentRun } from '@/types'
import { useState } from 'react'
import { Bot } from 'lucide-react'

export function AgentRunsPage() {
  const navigate = useNavigate()
  const { data: runs, loading, error, refetch } = useApi(getAgentRuns)
  const [search, setSearch] = useState('')

  const filtered = runs?.filter(r =>
    !search ||
    r.customer_name.toLowerCase().includes(search.toLowerCase()) ||
    r.payment_order_id.toLowerCase().includes(search.toLowerCase()) ||
    r.diagnosis.toLowerCase().includes(search.toLowerCase())
  ) ?? []

  const columns: Column<AgentRun>[] = [
    {
      key: 'id',
      header: 'Run ID',
      render: (row) => <span className="font-mono text-[12px] text-muted-foreground">{truncateId(row.id, 10)}</span>,
    },
    {
      key: 'payment_order_id',
      header: 'Payment',
      render: (row) => <span className="font-mono text-[12px] text-muted-foreground">{truncateId(row.payment_order_id, 12)}</span>,
    },
    {
      key: 'customer_name',
      header: 'Customer',
      sortable: true,
      render: (row) => <span className="font-medium text-[13px]">{row.customer_name}</span>,
    },
    {
      key: 'diagnosis',
      header: 'Diagnosis',
      sortable: true,
      render: (row) => (
        <div>
          <span className="font-mono text-[12px]">{row.diagnosis}</span>
          <span className="text-[10px] text-muted-foreground ml-1.5">{(row.confidence * 100).toFixed(0)}%</span>
        </div>
      ),
    },
    {
      key: 'decision',
      header: 'Decision',
      sortable: true,
      render: (row) => <StatusBadge status={row.status as never} />,
    },
    {
      key: 'risk_level',
      header: 'Risk',
      sortable: true,
      render: (row) => <StatusBadge status={row.risk_level.toLowerCase() as never} />,
    },
    {
      key: 'duration_ms',
      header: 'Duration',
      sortable: true,
      render: (row) => <span className="font-mono text-[12px] text-muted-foreground">{(row.duration_ms / 1000).toFixed(2)}s</span>,
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => <span className="text-muted-foreground text-[12px] whitespace-nowrap">{formatRelativeTime(row.created_at)}</span>,
    },
  ]

  return (
    <PageContainer title="Agent Runs" description="AI agent execution traces and diagnostics">
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search by customer, payment, or diagnosis..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-72 rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        />
      </div>

      {loading ? (
        <TableSkeleton rows={8} columns={8} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No agent runs yet"
          description="AI agent execution traces will appear here when failures are investigated"
          icon={<Bot className="w-8 h-8" />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          pageSize={10}
          onRowClick={(row) => navigate(`/agent-runs/${row.id}`)}
        />
      )}
    </PageContainer>
  )
}
