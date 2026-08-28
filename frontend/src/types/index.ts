export type PaymentStatus = 'created' | 'authorized' | 'captured' | 'failed' | 'recovery_pending' | 'refunded' | 'recovered'

export type IncidentStatus = 'new' | 'investigating' | 'recovery_pending' | 'recovered' | 'escalated'

export type RecoveryChannel = 'email' | 'sms' | 'whatsapp'

export type RecoveryAttemptStatus = 'pending' | 'sent' | 'opened' | 'recovered' | 'failed' | 'expired'

export type AgentRunStatus = 'running' | 'completed' | 'failed' | 'timeout'

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export type AuditResult = 'allowed' | 'blocked' | 'failed' | 'success'

export interface Payment {
  id: string
  razorpay_order_id: string
  razorpay_payment_id: string | null
  customer_id: string
  customer_name: string
  customer_email: string
  amount: number
  currency: string
  status: PaymentStatus
  failure_reason: string | null
  failure_code: string | null
  recovery_status: string | null
  created_at: string
  updated_at: string
}

export interface Incident {
  id: string
  payment_id: string
  payment_order_id: string
  customer_name: string
  customer_email: string
  amount: number
  failure_reason: string
  severity: Severity
  status: IncidentStatus
  recovery_state: string | null
  created_at: string
  updated_at: string
}

export interface RecoveryAttempt {
  id: string
  payment_id: string
  payment_order_id: string
  customer_name: string
  customer_email: string
  original_amount: number
  recovery_amount: number | null
  recovery_time: string | null
  channel: RecoveryChannel
  status: RecoveryAttemptStatus
  agent_run_id: string | null
  created_at: string
  sent_at: string | null
  opened_at: string | null
  recovered_at: string | null
}

export interface AgentStage {
  name: string
  status: 'completed' | 'failed' | 'skipped'
  input: Record<string, unknown>
  output: Record<string, unknown>
  duration_ms: number
  error?: string
}

export interface AgentRun {
  id: string
  payment_id: string
  payment_order_id: string
  customer_name: string
  customer_email: string
  diagnosis: string
  confidence: number
  decision: string
  risk_level: string
  status: AgentRunStatus
  stages: AgentStage[]
  duration_ms: number
  created_at: string
  completed_at: string | null
}

export interface AuditEvent {
  id: string
  timestamp: string
  action: string
  actor: string
  description: string
  resource_type: string
  resource_id: string
  result: AuditResult
  policy_name: string | null
  payload: Record<string, unknown>
}

export interface Policy {
  id: string
  name: string
  description: string
  value: string | number | boolean
  type: 'number' | 'boolean' | 'text'
  unit: string | null
  last_updated: string
  updated_by: string
}

export interface OverviewMetrics {
  total_revenue: number
  revenue_at_risk: number
  recovered_revenue: number
  failed_payments: number
  recovery_rate: number
  total_payments: number
  previous_period_revenue: number
  previous_period_recovered: number
  previous_period_failed: number
}

export interface DecisionReplay {
  payment_id: string
  payment_order_id: string
  customer_name: string
  amount: number
  stages: {
    event: { timestamp: string; data: Record<string, unknown> }
    agent: { timestamp: string; data: Record<string, unknown> }
    tools: { timestamp: string; data: Record<string, unknown> }
    diagnosis: { timestamp: string; data: Record<string, unknown> }
    policy: { timestamp: string; data: Record<string, unknown> }
    email: { timestamp: string; data: Record<string, unknown> }
    customer: { timestamp: string; data: Record<string, unknown> }
    payment: { timestamp: string; data: Record<string, unknown> }
  }
}

export interface ChartDataPoint {
  date: string
  value: number
  label?: string
}
