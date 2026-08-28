import { policies } from '@/mocks/policies'
import type { Policy } from '@/types'

export async function getPolicies(): Promise<Policy[]> {
  return policies
}

export async function updatePolicy(id: string, value: string | number | boolean): Promise<Policy> {
  const policy = policies.find(p => p.id === id)
  if (!policy) throw new Error('Policy not found')
  policy.value = value
  policy.last_updated = new Date().toISOString()
  policy.updated_by = 'Merchant'
  return policy
}
