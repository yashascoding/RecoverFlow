import { api } from './client'
import type { DecisionReplay } from '@/types'

export async function getDecisionReplay(paymentId: string): Promise<DecisionReplay | undefined> {
  try {
    return await api.get<DecisionReplay>(`/api/recovery/v2/replay/${paymentId}`)
  } catch {
    return undefined
  }
}
