import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getIncident } from '@/api/recovery'
import { formatCurrency, formatDateTime } from '@/lib/utils'

export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: incident, loading } = useApi(() => getIncident(id!), [id])

  if (loading) {
    return (
      <PageContainer title="Incident Details">
        <div className="h-48 bg-secondary animate-pulse rounded-lg" />
      </PageContainer>
    )
  }

  if (!incident) {
    return (
      <PageContainer title="Incident Details">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Incident not found</p>
          <Link to="/incidents" className="text-sm text-recovery hover:underline mt-2 inline-block">Back to Incidents</Link>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="Incident Details">
      <Link to="/incidents" className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Incidents
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Incident</h2>
            <StatusBadge status={incident.status} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              ['Incident ID', incident.id],
              ['Payment', incident.payment_order_id],
              ['Customer', incident.customer_name],
              ['Email', incident.customer_email],
              ['Amount', formatCurrency(incident.amount)],
              ['Severity', incident.severity],
              ['Failure Reason', incident.failure_reason],
              ['Created', formatDateTime(incident.created_at)],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</p>
                <p className="text-[13px] text-foreground mt-0.5">{value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">Timeline</h2>
          <div className="space-y-3">
            {[
              { time: incident.created_at, label: 'Incident created', status: 'completed' },
              { time: incident.created_at, label: 'AI agent investigating', status: incident.status !== 'new' ? 'completed' : 'pending' },
              { time: incident.updated_at, label: incident.status === 'recovered' ? 'Payment recovered' : 'Awaiting resolution', status: incident.status === 'recovered' ? 'completed' : 'pending' },
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${step.status === 'completed' ? 'bg-success' : 'bg-border'}`} />
                <div>
                  <p className="text-[13px] text-foreground">{step.label}</p>
                  <p className="text-[11px] text-muted-foreground">{formatDateTime(step.time)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
