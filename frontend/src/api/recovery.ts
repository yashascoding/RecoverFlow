import { api } from './client'
import type { Incident, RecoveryAttempt } from '@/types'

export async function getIncidents(): Promise<Incident[]> {
  return api.get<Incident[]>('/api/recovery/v2/incidents')
}

export async function getIncident(id: string): Promise<Incident> {
  return api.get<Incident>(`/api/recovery/v2/incidents/${id}`)
}

export async function getRecoveryAttempts(): Promise<RecoveryAttempt[]> {
  return api.get<RecoveryAttempt[]>('/api/recovery-attempts/')
}
