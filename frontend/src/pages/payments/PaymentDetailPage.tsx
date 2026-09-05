import { useParams, Link } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import { ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getPayment, checkRecoveryStatus } from '@/api/payments'
import { formatCurrency, formatDateTime } from '@/lib/utils'

const lifecycleSteps = [
  'created', 'authorized', 'captured', 'failed', 'recovery_pending', 'recovered'
]

export function PaymentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: payment, loading, refetch } = useApi(() => getPayment(id!), [id])
  const [checking, setChecking] = useState(false)
  const [checkMessage, setCheckMessage] = useState<string | null>(null)

  const handleCheckRecovery = useCallback(async () => {
    if (!id || checking) return
    setChecking(true)
    setCheckMessage(null)
    try {
      const result = await checkRecoveryStatus(id)
      setCheckMessage(result.message)
      if (result.new_status === 'recovered') {
        refetch()
      }
    } catch (err) {
      setCheckMessage(err instanceof Error ? err.message : 'Failed to check status')
    } finally {
      setChecking(false)
    }
  }, [id, checking, refetch])

  useEffect(() => {
    if (!payment || payment.status !== 'recovery_pending') return
    const interval = setInterval(() => {
      refetch()
    }, 10000)
    return () => clearInterval(interval)
  }, [payment?.status, refetch])

  if (loading) {
    return (
      <PageContainer title="Payment Details">
        <div className="space-y-4">
          <div className="h-8 w-32 bg-secondary animate-pulse rounded" />
          <div className="h-48 bg-secondary animate-pulse rounded-lg" />
        </div>
      </PageContainer>
    )
  }

  if (!payment) {
    return (
      <PageContainer title="Payment Details">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Payment not found</p>
          <Link to="/payments" className="text-sm text-recovery hover:underline mt-2 inline-block">
            Back to Payments
          </Link>
        </div>
      </PageContainer>
    )
  }

  const currentIdx = lifecycleSteps.indexOf(payment.status)

  return (
    <PageContainer
      title="Payment Details"
      actions={
        <Link
          to={`/replay/${payment.id}`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary text-[13px] font-medium text-foreground hover:bg-secondary/80 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Decision Replay
        </Link>
      }
    >
      <Link to="/payments" className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Payments
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Payment Info */}
        <div className="lg:col-span-2 rounded-lg border border-border bg-card p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-foreground">Payment</h2>
            <StatusBadge status={payment.status} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              ['Payment ID', payment.razorpay_order_id],
              ['Transaction ID', payment.razorpay_payment_id ?? '—'],
              ['Customer', payment.customer_name],
              ['Email', payment.customer_email],
              ['Amount', formatCurrency(payment.amount)],
              ['Currency', payment.currency],
              ['Failure Reason', payment.failure_reason ?? '—'],
              ['Created', formatDateTime(payment.created_at)],
            ].map(([label, value]) => (
              <div key={label}>
                <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</p>
                <p className="text-[13px] text-foreground mt-0.5 font-mono">{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Lifecycle */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground mb-4">Payment Lifecycle</h2>
          <div className="space-y-2">
            {lifecycleSteps.map((step, i) => {
              const isReached = i <= currentIdx
              const isCurrent = step === payment.status
              return (
                <div key={step} className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${
                    isCurrent ? 'bg-recovery ring-2 ring-recovery/30' :
                    isReached ? 'bg-success' : 'bg-border'
                  }`} />
                  <div className="flex-1">
                    <span className={`text-[12px] font-medium capitalize ${
                      isCurrent ? 'text-foreground' : isReached ? 'text-foreground' : 'text-muted-foreground'
                    }`}>
                      {step.replace(/_/g, ' ')}
                    </span>
                    {isCurrent && (
                      <span className="ml-2 text-[10px] text-recovery">← current</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recovery Attempts */}
      <div className="rounded-lg border border-border bg-card p-4 mt-4">
        <h2 className="text-sm font-semibold text-foreground mb-3">Recovery Attempts</h2>
        {payment.recovery_status ? (
            <div className="space-y-2">
            <div className="flex items-center gap-3 p-3 rounded-md bg-secondary/30">
              <StatusBadge status={payment.recovery_status as never} />
              <span className="text-[13px] text-foreground">Email recovery via Resend</span>
              <span className="text-[11px] text-muted-foreground ml-auto">1 attempt</span>
            </div>
          </div>
        ) : (
          <p className="text-[13px] text-muted-foreground">No recovery attempts</p>
        )}

        {(payment.status === 'recovery_pending' || payment.status === 'failed') && (
          <div className="mt-3 pt-3 border-t border-border">
            <button
              onClick={handleCheckRecovery}
              disabled={checking}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-recovery text-white text-[13px] font-medium hover:bg-recovery/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
              {checking ? 'Checking...' : 'Check Payment Status'}
            </button>
            {checkMessage && (
              <p className="text-[13px] text-muted-foreground mt-2">{checkMessage}</p>
            )}
            {payment.status === 'recovery_pending' && (
              <p className="text-[11px] text-muted-foreground mt-1">Auto-refreshing every 10s while pending</p>
            )}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
