import { payments, getPaymentById } from '@/mocks/payments'
import type { Payment } from '@/types'

export async function getPayments(): Promise<Payment[]> {
  return payments
}

export async function getPayment(id: string): Promise<Payment | undefined> {
  return getPaymentById(id)
}
