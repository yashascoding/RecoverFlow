import { api } from './client'
import type { Policy } from '@/types'

export async function getPolicies(): Promise<Policy[]> {
  return api.get<Policy[]>('/api/policies/')
}

export async function updatePolicy(id: string, value: string | number | boolean): Promise<Policy> {
  return api.patch<Policy>(`/api/policies/${id}`, { value })
}
