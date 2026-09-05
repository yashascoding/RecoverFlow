import { api } from './client'
import type { Payment } from '@/types'

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

interface RawPayment {
  id: string
  razorpay_order_id: string
  razorpay_payment_id: string | null
  customer_id?: string
  customer_email: string
  customer_name?: string
  amount: number
  currency: string
  status: string
  failure_reason: string | null
  created_at: string
  updated_at: string
}

export async function getPayments(): Promise<Payment[]> {
  const res = await api.get<PaginatedResponse<RawPayment>>('/api/payments/')
  return res.items.map((p) => ({
    id: p.id,
    razorpay_order_id: p.razorpay_order_id,
    razorpay_payment_id: p.razorpay_payment_id,
    customer_id: p.customer_id ?? '',
    customer_name: p.customer_name ?? p.customer_email.split('@')[0],
    customer_email: p.customer_email,
    amount: p.amount,
    currency: p.currency,
    status: p.status as Payment['status'],
    failure_reason: p.failure_reason,
    failure_code: null,
    recovery_status: p.status === 'recovered' ? 'recovered' : p.status === 'recovery_pending' ? 'recovery_pending' : null,
    created_at: p.created_at,
    updated_at: p.updated_at,
  }))
}

export async function getPayment(id: string): Promise<Payment> {
  const p = await api.get<RawPayment>(`/api/payments/${id}`)
  return {
    id: p.id,
    razorpay_order_id: p.razorpay_order_id,
    razorpay_payment_id: p.razorpay_payment_id,
    customer_id: p.customer_id ?? '',
    customer_name: p.customer_name ?? p.customer_email.split('@')[0],
    customer_email: p.customer_email,
    amount: p.amount,
    currency: p.currency,
    status: p.status as Payment['status'],
    failure_reason: p.failure_reason,
    failure_code: null,
    recovery_status: p.status === 'recovered' ? 'recovered' : p.status === 'recovery_pending' ? 'recovery_pending' : null,
    created_at: p.created_at,
    updated_at: p.updated_at,
  }
}

export interface RecoveryCheckResult {
  payment_id: string
  checked_at: string
  payment_link_status?: string
  new_status?: string
  message: string
  error?: string
}

export async function checkRecoveryStatus(paymentId: string): Promise<RecoveryCheckResult> {
  return api.post<RecoveryCheckResult>(`/api/payments/${paymentId}/check-recovery`)
}
