import type { Payment } from '@/types'

const customers = [
  { name: 'Rahul Sharma', email: 'rahul.sharma@gmail.com' },
  { name: 'Priya Patel', email: 'priya.patel@gmail.com' },
  { name: 'Amit Kumar', email: 'amit.kumar@gmail.com' },
  { name: 'Sneha Reddy', email: 'sneha.reddy@gmail.com' },
  { name: 'Vikram Singh', email: 'vikram.singh@gmail.com' },
  { name: 'Ananya Gupta', email: 'ananya.gupta@gmail.com' },
  { name: 'Rohan Joshi', email: 'rohan.joshi@gmail.com' },
  { name: 'Kavya Nair', email: 'kavya.nair@gmail.com' },
  { name: 'Arjun Mehta', email: 'arjun.mehta@gmail.com' },
  { name: 'Deepa Iyer', email: 'deepa.iyer@gmail.com' },
  { name: 'Sanjay Verma', email: 'sanjay.verma@gmail.com' },
  { name: 'Pooja Desai', email: 'pooja.desai@gmail.com' },
  { name: 'Karthik Menon', email: 'karthik.menon@gmail.com' },
  { name: 'Nisha Agarwal', email: 'nisha.agarwal@gmail.com' },
  { name: 'Ravi Prasad', email: 'ravi.prasad@gmail.com' },
]

const failureReasons = [
  { code: 'INSUFFICIENT_FUNDS', reason: 'Insufficient funds in your account.' },
  { code: 'UPI_TIMEOUT', reason: 'The UPI session timed out. Please try again.' },
  { code: 'BANK_DECLINED', reason: 'Your card was declined by the issuing bank.' },
  { code: 'NETWORK_ERROR', reason: 'A network error occurred during the transaction.' },
  { code: 'GATEWAY_ERROR', reason: 'Payment gateway service unavailable. Please retry.' },
  { code: 'FRAUD_CHECK', reason: 'Transaction flagged for security review.' },
]

const amounts = [49900, 99900, 149900, 199900, 249900, 349900, 499900, 99900, 59900, 79900]

function makeId(prefix: string, idx: number): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let hash = ''
  for (let i = 0; i < 14; i++) {
    hash += chars[(idx * 7 + i * 13) % chars.length]
  }
  return `${prefix}_${hash}`
}

function makeDate(daysAgo: number, hoursAgo: number = 0): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  d.setHours(d.getHours() - hoursAgo)
  return d.toISOString()
}

const statuses: Payment['status'][] = ['captured', 'captured', 'captured', 'captured', 'failed', 'failed', 'failed', 'recovery_pending', 'recovered', 'recovered']

export const payments: Payment[] = Array.from({ length: 30 }, (_, i) => {
  const customer = customers[i % customers.length]
  const amount = amounts[i % amounts.length]
  const status = statuses[i % statuses.length]
  const failed = status === 'failed' || status === 'recovery_pending' || status === 'recovered'
  const failure = failed ? failureReasons[i % failureReasons.length] : null

  return {
    id: makeId('pay', i),
    razorpay_order_id: makeId('order', i),
    razorpay_payment_id: status !== 'created' ? makeId('pay', i + 100) : null,
    customer_id: makeId('cust', i),
    customer_name: customer.name,
    customer_email: customer.email,
    amount,
    currency: 'INR',
    status,
    failure_reason: failure?.reason ?? null,
    failure_code: failure?.code ?? null,
    recovery_status: status === 'recovery_pending' ? 'email_sent' : status === 'recovered' ? 'recovered' : null,
    created_at: makeDate(Math.floor(i / 3), i % 24),
    updated_at: makeDate(Math.floor(i / 4), i % 12),
  }
})

export function getPaymentById(id: string): Payment | undefined {
  return payments.find(p => p.id === id || p.razorpay_order_id === id)
}
