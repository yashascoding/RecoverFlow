import { api } from './client'
import type { AuditEvent } from '@/types'

export async function getAuditEvents(): Promise<AuditEvent[]> {
  return api.get<AuditEvent[]>('/api/audit/')
}
