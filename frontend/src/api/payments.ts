import { api } from './client'
import type { Payment } from '@/types'

export async function getPayments(): Promise<Payment[]> {
  return api.get<Payment[]>('/api/payments/')
}

export async function getPayment(id: string): Promise<Payment> {
  return api.get<Payment>(`/api/payments/${id}`)
}
