import { cn } from '@/lib/utils'
import type { PaymentStatus, IncidentStatus, RecoveryAttemptStatus, AgentRunStatus, AuditResult, Severity } from '@/types'

type StatusType = PaymentStatus | IncidentStatus | RecoveryAttemptStatus | AgentRunStatus | AuditResult | Severity

const statusStyles: Record<string, string> = {
  captured: 'bg-success/15 text-success border-success/20',
  recovered: 'bg-success/15 text-success border-success/20',
  success: 'bg-success/15 text-success border-success/20',
  allowed: 'bg-success/15 text-success border-success/20',
  healthy: 'bg-success/15 text-success border-success/20',
  completed: 'bg-success/15 text-success border-success/20',
  failed: 'bg-destructive/15 text-red-400 border-destructive/20',
  blocked: 'bg-destructive/15 text-red-400 border-destructive/20',
  expired: 'bg-destructive/15 text-red-400 border-destructive/20',
  recovery_pending: 'bg-recovery/15 text-recovery border-recovery/20',
  pending: 'bg-recovery/15 text-recovery border-recovery/20',
  investigating: 'bg-recovery/15 text-recovery border-recovery/20',
  escalated: 'bg-warning/15 text-warning border-warning/20',
  new: 'bg-warning/15 text-warning border-warning/20',
  sent: 'bg-info/15 text-info border-info/20',
  opened: 'bg-info/15 text-info border-info/20',
  running: 'bg-recovery/15 text-recovery border-recovery/20',
  created: 'bg-secondary text-muted-foreground border-border',
  authorized: 'bg-secondary text-muted-foreground border-border',
  refunded: 'bg-secondary text-muted-foreground border-border',
  low: 'bg-secondary text-muted-foreground border-border',
  medium: 'bg-warning/15 text-warning border-warning/20',
  high: 'bg-orange-500/15 text-orange-400 border-orange-500/20',
  critical: 'bg-destructive/15 text-red-400 border-destructive/20',
}

const statusLabels: Record<string, string> = {
  recovery_pending: 'Recovery Pending',
  payment_failed: 'Payment Failed',
}

interface StatusBadgeProps {
  status: StatusType
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = statusLabels[status] || status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ')
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium capitalize',
        statusStyles[status] || 'bg-secondary text-muted-foreground border-border',
        className
      )}
    >
      {label}
    </span>
  )
}
