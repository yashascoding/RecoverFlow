import { useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { DataTable, type Column } from '@/components/dashboard/DataTable'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { TableSkeleton } from '@/components/dashboard/LoadingState'
import { ErrorState } from '@/components/dashboard/ErrorState'
import { EmptyState } from '@/components/dashboard/EmptyState'
import { useApi } from '@/hooks/useApi'
import { getPayments } from '@/api/payments'
import { formatCurrency, formatDateTime, truncateId } from '@/lib/utils'
import type { Payment } from '@/types'
import { useState } from 'react'
import { CreditCard } from 'lucide-react'

export function PaymentsPage() {
  const navigate = useNavigate()
  const { data: payments, loading, error, refetch } = useApi(getPayments)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const filtered = payments?.filter(p => {
    const matchSearch = !search ||
      p.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      p.customer_email.toLowerCase().includes(search.toLowerCase()) ||
      p.razorpay_order_id.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || p.status === statusFilter
    return matchSearch && matchStatus
  }) ?? []

  const columns: Column<Payment>[] = [
    {
      key: 'razorpay_order_id',
      header: 'Payment ID',
      sortable: true,
      render: (row) => (
        <span className="font-mono text-[12px] text-muted-foreground">{truncateId(row.razorpay_order_id, 12)}</span>
      ),
    },
    {
      key: 'customer_name',
      header: 'Customer',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-medium text-[13px]">{row.customer_name}</p>
          <p className="text-[11px] text-muted-foreground">{row.customer_email}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Amount',
      sortable: true,
      render: (row) => <span className="font-mono text-[13px]">{formatCurrency(row.amount)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'failure_reason',
      header: 'Failure Reason',
      render: (row) => (
        <span className="text-muted-foreground text-[12px] max-w-[200px] truncate block">
          {row.failure_reason ?? '—'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (row) => (
        <span className="text-muted-foreground text-[12px] whitespace-nowrap">{formatDateTime(row.created_at)}</span>
      ),
    },
    {
      key: 'recovery_status',
      header: 'Recovery',
      render: (row) => row.recovery_status ? <StatusBadge status={row.recovery_status as never} /> : <span className="text-muted-foreground text-[12px]">—</span>,
    },
  ]

  return (
    <PageContainer
      title="Payments"
      description="All payment transactions and their status"
    >
      {/* Filters */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Search by ID, customer, or email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-8 w-64 rounded-md border border-border bg-secondary/50 px-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-8 rounded-md border border-border bg-secondary/50 px-2 text-[13px] text-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
        >
          <option value="all">All Statuses</option>
          <option value="captured">Captured</option>
          <option value="failed">Failed</option>
          <option value="recovery_pending">Recovery Pending</option>
          <option value="recovered">Recovered</option>
        </select>
      </div>

      {loading ? (
        <TableSkeleton rows={8} columns={7} />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No payments yet"
          description="Payments will appear here once Razorpay webhooks are received"
          icon={<CreditCard className="w-8 h-8" />}
        />
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          pageSize={10}
          onRowClick={(row) => navigate(`/payments/${row.razorpay_order_id}`)}
        />
      )}
    </PageContainer>
  )
}
