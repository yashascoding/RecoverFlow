import type { DecisionReplay } from '@/types'

const replays: Record<string, DecisionReplay> = {
  'pay_7f82a91c': {
    payment_id: 'pay_7f82a91c',
    payment_order_id: 'order_7f82a91c',
    customer_name: 'Rahul Sharma',
    amount: 249900,
    stages: {
      event: {
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        data: { type: 'payment.failed', failure_code: 'INSUFFICIENT_FUNDS', amount: 249900 },
      },
      agent: {
        timestamp: new Date(Date.now() - 3599000).toISOString(),
        data: { run_id: 'run_001', status: 'started', stages: ['OBSERVE', 'INVESTIGATE', 'DIAGNOSE', 'PLAN'] },
      },
      tools: {
        timestamp: new Date(Date.now() - 3598000).toISOString(),
        data: { tools_called: ['fetch_customer', 'fetch_payment', 'check_consent', 'diagnose_failure'] },
      },
      diagnosis: {
        timestamp: new Date(Date.now() - 3597000).toISOString(),
        data: { diagnosis: 'insufficient_funds', confidence: 0.94, risk_level: 'LOW', reasoning: 'Customer has good payment history. Temporary insufficient funds.' },
      },
      policy: {
        timestamp: new Date(Date.now() - 3596000).toISOString(),
        data: { checks: [
          { name: 'MAX_AUTO_PAYMENT', result: 'PASS', details: '₹2,499 ≤ ₹5,000 limit' },
          { name: 'EMAIL_CONSENT', result: 'PASS', details: 'Customer has granted consent' },
          { name: 'DAILY_EMAIL_LIMIT', result: 'PASS', details: '0/3 emails sent today' },
        ]},
      },
      email: {
        timestamp: new Date(Date.now() - 3595000).toISOString(),
        data: { template: 'payment_failure', sent: true, to: 'rahul.sharma@gmail.com', provider: 'resend' },
      },
      customer: {
        timestamp: new Date(Date.now() - 3570000).toISOString(),
        data: { action: 'opened_email', timestamp: new Date(Date.now() - 3570000).toISOString() },
      },
      payment: {
        timestamp: new Date(Date.now() - 3240000).toISOString(),
        data: { status: 'recovered', amount: 249900, recovered_at: new Date(Date.now() - 3240000).toISOString() },
      },
    },
  },
}

export async function getDecisionReplay(paymentId: string): Promise<DecisionReplay | undefined> {
  return replays[paymentId]
}
