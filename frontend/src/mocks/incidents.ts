import type { Incident } from '@/types'

export const incidents: Incident[] = [
  {
    id: 'inc_001', payment_id: 'pay_7f82a91c', payment_order_id: 'order_7f82a91c',
    customer_name: 'Rahul Sharma', customer_email: 'rahul.sharma@gmail.com',
    amount: 249900, failure_reason: 'Insufficient funds in your account.',
    severity: 'medium', status: 'recovered', recovery_state: 'recovered',
    created_at: new Date(Date.now() - 3600000).toISOString(), updated_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 'inc_002', payment_id: 'pay_3b4e7d2a', payment_order_id: 'order_3b4e7d2a',
    customer_name: 'Priya Patel', customer_email: 'priya.patel@gmail.com',
    amount: 420000, failure_reason: 'The UPI session timed out. Please try again.',
    severity: 'high', status: 'recovery_pending', recovery_state: 'email_sent',
    created_at: new Date(Date.now() - 7200000).toISOString(), updated_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'inc_003', payment_id: 'pay_9c1f5e8b', payment_order_id: 'order_9c1f5e8b',
    customer_name: 'Amit Kumar', customer_email: 'amit.kumar@gmail.com',
    amount: 159900, failure_reason: 'Your card was declined by the issuing bank.',
    severity: 'low', status: 'recovered', recovery_state: 'recovered',
    created_at: new Date(Date.now() - 14400000).toISOString(), updated_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 'inc_004', payment_id: 'pay_2d6a8c4f', payment_order_id: 'order_2d6a8c4f',
    customer_name: 'Sneha Reddy', customer_email: 'sneha.reddy@gmail.com',
    amount: 89900, failure_reason: 'A network error occurred during the transaction.',
    severity: 'low', status: 'new', recovery_state: null,
    created_at: new Date(Date.now() - 21600000).toISOString(), updated_at: new Date(Date.now() - 21600000).toISOString(),
  },
  {
    id: 'inc_005', payment_id: 'pay_5e3b7a1d', payment_order_id: 'order_5e3b7a1d',
    customer_name: 'Vikram Singh', customer_email: 'vikram.singh@gmail.com',
    amount: 349900, failure_reason: 'Payment gateway service unavailable. Please retry.',
    severity: 'medium', status: 'investigating', recovery_state: null,
    created_at: new Date(Date.now() - 28800000).toISOString(), updated_at: new Date(Date.now() - 25200000).toISOString(),
  },
  {
    id: 'inc_006', payment_id: 'pay_8a1c3e5f', payment_order_id: 'order_8a1c3e5f',
    customer_name: 'Ananya Gupta', customer_email: 'ananya.gupta@gmail.com',
    amount: 499900, failure_reason: 'Transaction flagged for security review.',
    severity: 'critical', status: 'escalated', recovery_state: null,
    created_at: new Date(Date.now() - 43200000).toISOString(), updated_at: new Date(Date.now() - 36000000).toISOString(),
  },
  {
    id: 'inc_007', payment_id: 'pay_4f7b2e9a', payment_order_id: 'order_4f7b2e9a',
    customer_name: 'Rohan Joshi', customer_email: 'rohan.joshi@gmail.com',
    amount: 99900, failure_reason: 'Insufficient funds in your account.',
    severity: 'low', status: 'recovered', recovery_state: 'recovered',
    created_at: new Date(Date.now() - 86400000).toISOString(), updated_at: new Date(Date.now() - 72000000).toISOString(),
  },
  {
    id: 'inc_008', payment_id: 'pay_6d2f8c1b', payment_order_id: 'order_6d2f8c1b',
    customer_name: 'Kavya Nair', customer_email: 'kavya.nair@gmail.com',
    amount: 199900, failure_reason: 'The UPI session timed out. Please try again.',
    severity: 'medium', status: 'recovery_pending', recovery_state: 'email_sent',
    created_at: new Date(Date.now() - 100800000).toISOString(), updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 'inc_009', payment_id: 'pay_1e5a9d3c', payment_order_id: 'order_1e5a9d3c',
    customer_name: 'Arjun Mehta', customer_email: 'arjun.mehta@gmail.com',
    amount: 79900, failure_reason: 'Your card was declined by the issuing bank.',
    severity: 'low', status: 'recovered', recovery_state: 'recovered',
    created_at: new Date(Date.now() - 172800000).toISOString(), updated_at: new Date(Date.now() - 144000000).toISOString(),
  },
  {
    id: 'inc_010', payment_id: 'pay_7b3c6f2e', payment_order_id: 'order_7b3c6f2e',
    customer_name: 'Deepa Iyer', customer_email: 'deepa.iyer@gmail.com',
    amount: 349900, failure_reason: 'A network error occurred during the transaction.',
    severity: 'medium', status: 'new', recovery_state: null,
    created_at: new Date(Date.now() - 259200000).toISOString(), updated_at: new Date(Date.now() - 259200000).toISOString(),
  },
]
