import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, Clock } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { useApi } from '@/hooks/useApi'
import { getDecisionReplay } from '@/api/replay'
import { formatCurrency, formatDateTime } from '@/lib/utils'
import { useState } from 'react'

interface StageConfig {
  key: string
  label: string
  icon: string
  description: string
  resultKey?: string
  resultLabel?: string
}

const stages: StageConfig[] = [
  { key: 'event', label: 'Payment Failed', icon: '💥', description: 'Failure event received from Razorpay' },
  { key: 'agent', label: 'AI Investigator', icon: '🤖', description: 'Agent workflow initiated' },
  { key: 'tools', label: 'Tool Execution', icon: '🔧', description: 'Customer data and payment history fetched' },
  { key: 'diagnosis', label: 'Diagnosis', icon: '🧠', description: 'Root cause identified with confidence score' },
  { key: 'policy', label: 'Policy Firewall', icon: '🛡', description: 'Policy rules evaluated against recovery action' },
  { key: 'email', label: 'Email Sent', icon: '📧', description: 'Recovery email delivered to customer' },
  { key: 'customer', label: 'Customer Action', icon: '👤', description: 'Customer opened email and clicked payment link' },
  { key: 'payment', label: 'Payment Recovered', icon: '✅', description: 'Payment successfully captured' },
]

export function DecisionReplayPage() {
  const { paymentId } = useParams<{ paymentId: string }>()
  const { data: replay, loading } = useApi(() => getDecisionReplay(paymentId!), [paymentId])
  const [expandedStage, setExpandedStage] = useState<string | null>(null)

  if (loading) {
    return (
      <PageContainer title="Decision Replay">
        <div className="h-96 bg-secondary animate-pulse rounded-lg" />
      </PageContainer>
    )
  }

  if (!replay) {
    return (
      <PageContainer title="Decision Replay">
        <div className="text-center py-12">
          <p className="text-muted-foreground">No replay data available for this payment</p>
          <Link to="/payments" className="text-sm text-recovery hover:underline mt-2 inline-block">Back to Payments</Link>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer
      title="Decision Replay"
      description={`Replay the complete recovery decision for ${replay.payment_order_id}`}
    >
      <Link to="/payments" className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Payments
      </Link>

      {/* Summary */}
      <div className="rounded-lg border border-border bg-card p-4 mb-6">
        <div className="flex items-center gap-6">
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Customer</p>
            <p className="text-sm font-medium text-foreground">{replay.customer_name}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Amount</p>
            <p className="text-sm font-bold font-mono text-foreground">{formatCurrency(replay.amount)}</p>
          </div>
          <div className="ml-auto">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-success/15 text-success border border-success/20 text-[12px] font-medium">
              <CheckCircle className="w-3.5 h-3.5" />
              RECOVERED
            </span>
          </div>
        </div>
      </div>

      {/* Visual Flow */}
      <div className="relative">
        {/* Vertical connector line */}
        <div className="absolute left-[19px] top-8 bottom-8 w-0.5 bg-gradient-to-b from-recovery via-success to-success" />

        <div className="space-y-0">
          {stages.map((stage, i) => {
            const stageData = replay.stages[stage.key as keyof typeof replay.stages]
            const isExpanded = expandedStage === stage.key
            const isLast = i === stages.length - 1

            return (
              <div key={stage.key} className="relative">
                <button
                  onClick={() => setExpandedStage(isExpanded ? null : stage.key)}
                  className="flex items-start gap-4 w-full text-left group py-3"
                >
                  {/* Icon circle */}
                  <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0 border-2 ${
                    isLast ? 'bg-success/15 border-success' : 'bg-card border-border group-hover:border-recovery'
                  } transition-colors`}>
                    {stage.icon}
                  </div>

                  <div className="flex-1 min-w-0 pt-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-foreground">{stage.label}</h3>
                      {stageData && (
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {formatDateTime(stageData.timestamp)}
                        </span>
                      )}
                    </div>
                    <p className="text-[13px] text-muted-foreground mt-0.5">{stage.description}</p>
                  </div>

                  <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors pt-1">
                    {isExpanded ? 'Collapse' : 'View details'}
                  </span>
                </button>

                {/* Expanded content */}
                {isExpanded && stageData && (
                  <div className="ml-14 mb-4 p-4 rounded-lg bg-secondary/30 border border-border">
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Metadata</p>
                        <pre className="text-[11px] text-foreground font-mono bg-background/50 rounded p-3 overflow-x-auto max-h-48">
                          {JSON.stringify(stageData.data, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}

                {/* Connector dot between stages */}
                {!isLast && (
                  <div className="absolute left-[18px] -bottom-0.5 w-2 h-2 rounded-full bg-border" />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </PageContainer>
  )
}
