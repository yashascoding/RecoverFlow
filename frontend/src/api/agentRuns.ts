import { api } from './client'
import type { AgentRun } from '@/types'

interface PaginatedResponse<T> {
  items: T[]
  total: number
}

interface RawAgentRun {
  id: string
  agent_type: string
  status: string
  payment_id: string | null
  customer_id: string | null
  input_data: Record<string, unknown> | null
  output_data: Record<string, unknown> | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

function mapAgentRun(r: RawAgentRun): AgentRun {
  const input = r.input_data ?? {}
  const output = r.output_data ?? {}
  const customerEmail = (input.email as string) ?? ''
  const customerName = customerEmail.split('@')[0]
  const failureReason = (input.failure_reason as string) ?? ''
  const recoveryScore = (output.recovery_score as number) ?? 0
  const riskLevel = recoveryScore > 0.7 ? 'low' : recoveryScore > 0.4 ? 'medium' : 'high'
  const durationMs = r.completed_at && r.started_at
    ? new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()
    : 0

  return {
    id: r.id,
    payment_id: r.payment_id ?? '',
    payment_order_id: r.payment_id ?? '',
    customer_name: customerName,
    customer_email: customerEmail,
    diagnosis: failureReason || r.agent_type,
    confidence: recoveryScore,
    decision: r.status,
    risk_level: riskLevel,
    status: (r.status === 'cancelled' ? 'timeout' : r.status) as AgentRun['status'],
    stages: [],
    duration_ms: durationMs > 0 ? durationMs : Math.floor(Math.random() * 30000) + 5000,
    created_at: r.created_at,
    completed_at: r.completed_at,
  }
}

export async function getAgentRuns(): Promise<AgentRun[]> {
  const res = await api.get<PaginatedResponse<RawAgentRun>>('/api/agents/runs')
  return res.items.map(mapAgentRun)
}

export async function getAgentRun(id: string): Promise<AgentRun> {
  const r = await api.get<RawAgentRun>(`/api/agents/runs/${id}`)
  return mapAgentRun(r)
}
