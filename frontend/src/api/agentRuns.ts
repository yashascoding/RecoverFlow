import { api } from './client'
import type { AgentRun, AgentStage } from '@/types'

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

interface RawTraceStage {
  stage: string
  latency_ms: number
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  tool_calls?: Array<{
    tool_name: string
    latency_ms: number
    result?: Record<string, unknown>
    error?: string | null
  }>
  error?: string | null
  started_at?: string
  completed_at?: string
}

function mapAgentRun(r: RawAgentRun): AgentRun {
  const input = r.input_data ?? {}
  const output = r.output_data ?? {}
  const customerEmail = (input.email as string) ?? ''
  const customerName = customerEmail.split('@')[0]
  const failureReason = (input.failure_reason as string) ?? ''

  const trace = (output.trace as Record<string, unknown>) ?? {}
  const rawStages = (trace.stages as RawTraceStage[]) ?? []

  const stages: AgentStage[] = rawStages.map((s) => ({
    name: s.stage,
    status: s.error ? 'failed' : 'completed',
    input: s.input_data ?? {},
    output: s.output_data ?? {},
    duration_ms: Math.round(s.latency_ms ?? 0),
    error: s.error ?? undefined,
  }))

  const totalLatencyMs = (trace.total_latency_ms as number)
    ?? (r.completed_at && r.started_at
      ? new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()
      : 0)

  const diagnoseStage = rawStages.find((s) => s.stage === 'diagnose')
  const planStage = rawStages.find((s) => s.stage === 'plan')
  const diagOutput = (diagnoseStage?.output_data ?? {}) as Record<string, unknown>
  const planOutput = (planStage?.output_data ?? {}) as Record<string, unknown>

  const diagnosis = (diagOutput.diagnosis as string)
    || (diagOutput.reason as string)
    || failureReason
    || r.agent_type

  const confidence = (diagOutput.confidence as number) ?? 0
  const riskLevel = (diagOutput.risk_level as string)?.toLowerCase()
    ?? (confidence > 0.7 ? 'low' : confidence > 0.4 ? 'medium' : 'high')

  const recommendedAction = (diagOutput.recommended_action as string)
    ?? (planOutput.recommended_actions as Array<{ type: string }>)?.[0]?.type
    ?? r.status

  return {
    id: r.id,
    payment_id: r.payment_id ?? '',
    payment_order_id: r.payment_id ?? '',
    customer_name: customerName,
    customer_email: customerEmail,
    diagnosis,
    confidence,
    decision: recommendedAction,
    risk_level: riskLevel,
    status: (r.status === 'cancelled' ? 'timeout' : r.status) as AgentRun['status'],
    stages,
    duration_ms: totalLatencyMs > 0 ? totalLatencyMs : 0,
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
