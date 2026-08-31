import { api } from './client'
import type { AgentRun } from '@/types'

export async function getAgentRuns(): Promise<AgentRun[]> {
  return api.get<AgentRun[]>('/api/agents/runs')
}

export async function getAgentRun(id: string): Promise<AgentRun> {
  return api.get<AgentRun>(`/api/agents/runs/${id}`)
}
