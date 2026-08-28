import { auditEvents } from '@/mocks/audit'
import type { AuditEvent } from '@/types'

export async function getAuditEvents(): Promise<AuditEvent[]> {
  return auditEvents
}
