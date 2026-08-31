import { api } from './client'
import type { Incident, RecoveryAttempt } from '@/types'

interface RawIncident {
  id: string
  payment_id: string
  payment_order_id: string
  customer_name: string
  customer_email: string
  amount: number
  failure_reason: string
  severity: string
  status: string
  recovery_state: string | null
  created_at: string
  updated_at: string
}

interface RawRecoveryAttempt {
  id: string
  payment_id: string
  payment_order_id: string
  customer_name: string
  customer_email: string
  original_amount: number
  recovery_amount: number | null
  recovery_time: string | null
  channel: string
  status: string
  agent_run_id: string | null
  created_at: string
  sent_at: string | null
  opened_at: string | null
  recovered_at: string | null
}

export async function getIncidents(): Promise<Incident[]> {
  const res = await api.get<RawIncident[]>('/api/recovery/v2/incidents')
  return res.map((i) => ({
    id: i.id,
    payment_id: i.payment_id,
    payment_order_id: i.payment_order_id,
    customer_name: i.customer_name,
    customer_email: i.customer_email,
    amount: i.amount,
    failure_reason: i.failure_reason,
    severity: i.severity as Incident['severity'],
    status: i.status as Incident['status'],
    recovery_state: i.recovery_state,
    created_at: i.created_at,
    updated_at: i.updated_at,
  }))
}

export async function getIncident(id: string): Promise<Incident> {
  const res = await api.get<RawIncident>(`/api/recovery/v2/incidents?id=${id}`)
  return {
    id: res.id,
    payment_id: res.payment_id,
    payment_order_id: res.payment_order_id,
    customer_name: res.customer_name,
    customer_email: res.customer_email,
    amount: res.amount,
    failure_reason: res.failure_reason,
    severity: res.severity as Incident['severity'],
    status: res.status as Incident['status'],
    recovery_state: res.recovery_state,
    created_at: res.created_at,
    updated_at: res.updated_at,
  }
}

export async function getRecoveryAttempts(): Promise<RecoveryAttempt[]> {
  const res = await api.get<RawRecoveryAttempt[]>('/api/recovery-attempts/')
  return res.map((a) => ({
    id: a.id,
    payment_id: a.payment_id,
    payment_order_id: a.payment_order_id,
    customer_name: a.customer_name,
    customer_email: a.customer_email,
    original_amount: a.original_amount,
    recovery_amount: a.recovery_amount,
    recovery_time: a.recovery_time,
    channel: a.channel as RecoveryAttempt['channel'],
    status: a.status as RecoveryAttempt['status'],
    agent_run_id: a.agent_run_id,
    created_at: a.created_at,
    sent_at: a.sent_at,
    opened_at: a.opened_at,
    recovered_at: a.recovered_at,
  }))
}
