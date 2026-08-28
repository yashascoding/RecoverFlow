import { agentRuns } from '@/mocks/agentRuns'
import type { AgentRun } from '@/types'

export async function getAgentRuns(): Promise<AgentRun[]> {
  return agentRuns
}

export async function getAgentRun(id: string): Promise<AgentRun | undefined> {
  return agentRuns.find(r => r.id === id)
}
