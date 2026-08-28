import { incidents } from '@/mocks/incidents'
import { recoveryAttempts } from '@/mocks/recovery'
import type { Incident, RecoveryAttempt } from '@/types'

export async function getIncidents(): Promise<Incident[]> {
  return incidents
}

export async function getIncident(id: string): Promise<Incident | undefined> {
  return incidents.find(i => i.id === id)
}

export async function getRecoveryAttempts(): Promise<RecoveryAttempt[]> {
  return recoveryAttempts
}
