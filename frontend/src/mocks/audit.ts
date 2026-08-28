import type { AuditEvent } from '@/types'

export const auditEvents: AuditEvent[] = [
  {
    id: 'aud_001', timestamp: new Date(Date.now() - 120000).toISOString(),
    action: 'SEND_RECOVERY_EMAIL', actor: 'AI_AGENT', description: 'Recovery email sent to customer',
    resource_type: 'recovery_attempt', resource_id: 'rec_001', result: 'success',
    policy_name: 'EMAIL_CONSENT_REQUIRED', payload: { channel: 'email', template: 'payment_failure' },
  },
  {
    id: 'aud_002', timestamp: new Date(Date.now() - 300000).toISOString(),
    action: 'RECOVERY_DECISION', actor: 'AI_AGENT', description: 'Agent recommended EMAIL_PAYMENT_LINK',
    resource_type: 'agent_run', resource_id: 'run_001', result: 'allowed',
    policy_name: null, payload: { decision: 'EMAIL_PAYMENT_LINK', confidence: 0.94 },
  },
  {
    id: 'aud_003', timestamp: new Date(Date.now() - 310000).toISOString(),
    action: 'POLICY_EVALUATED', actor: 'POLICY_ENGINE', description: 'Payment amount within auto-recovery limit',
    resource_type: 'payment', resource_id: 'pay_7f82a91c', result: 'allowed',
    policy_name: 'MAX_AUTO_PAYMENT', payload: { amount: 249900, limit: 500000 },
  },
  {
    id: 'aud_004', timestamp: new Date(Date.now() - 600000).toISOString(),
    action: 'PAYMENT_FAILED', actor: 'SYSTEM', description: 'Payment failed: insufficient_funds',
    resource_type: 'payment', resource_id: 'pay_3b4e7d2a', result: 'success',
    policy_name: null, payload: { failure_code: 'INSUFFICIENT_FUNDS', amount: 420000 },
  },
  {
    id: 'aud_005', timestamp: new Date(Date.now() - 900000).toISOString(),
    action: 'RECOVERY_EMAIL_SENT', actor: 'EMAIL_SERVICE', description: 'Recovery email delivered via Resend',
    resource_type: 'email_message', resource_id: 'msg_001', result: 'success',
    policy_name: null, payload: { provider: 'resend', to: 'priya.patel@gmail.com' },
  },
  {
    id: 'aud_006', timestamp: new Date(Date.now() - 1800000).toISOString(),
    action: 'POLICY_BLOCK', actor: 'POLICY_ENGINE', description: 'Amount exceeded auto-recovery threshold',
    resource_type: 'payment', resource_id: 'pay_a8c3e1d5', result: 'blocked',
    policy_name: 'MAX_AUTO_PAYMENT', payload: { amount: 99900, limit: 500000 },
  },
  {
    id: 'aud_007', timestamp: new Date(Date.now() - 2400000).toISOString(),
    action: 'AGENT_DIAGNOSIS', actor: 'AI_AGENT', description: 'Fraud check flagged — blocking recovery',
    resource_type: 'agent_run', resource_id: 'run_007', result: 'blocked',
    policy_name: 'FRAUD_CHECK', payload: { diagnosis: 'fraud_check', risk_level: 'HIGH' },
  },
  {
    id: 'aud_008', timestamp: new Date(Date.now() - 3600000).toISOString(),
    action: 'PAYMENT_RECOVERED', actor: 'SYSTEM', description: 'Payment status: recovery_pending → recovered',
    resource_type: 'payment', resource_id: 'pay_9c1f5e8b', result: 'success',
    policy_name: null, payload: { old_status: 'recovery_pending', new_status: 'recovered', amount: 159900 },
  },
  {
    id: 'aud_009', timestamp: new Date(Date.now() - 5400000).toISOString(),
    action: 'CONSENT_GRANTED', actor: 'CUSTOMER', description: 'Customer granted email consent',
    resource_type: 'customer', resource_id: 'cust_003', result: 'success',
    policy_name: null, payload: { channel: 'email', source: 'checkout' },
  },
  {
    id: 'aud_010', timestamp: new Date(Date.now() - 7200000).toISOString(),
    action: 'RECOVERY_ATTEMPTED', actor: 'RECOVERY_PIPELINE', description: 'Recovery initiated for ₹2,499',
    resource_type: 'payment', resource_id: 'pay_7f82a91c', result: 'success',
    policy_name: null, payload: { recovery_attempt_id: 'rec_001', channel: 'email' },
  },
  {
    id: 'aud_011', timestamp: new Date(Date.now() - 10800000).toISOString(),
    action: 'KILL_SWITCH_CHECK', actor: 'POLICY_ENGINE', description: 'Kill switch is OFF — recovery allowed',
    resource_type: 'system', resource_id: 'policy_kill_switch', result: 'allowed',
    policy_name: 'KILL_SWITCH', payload: { kill_switch: false },
  },
  {
    id: 'aud_012', timestamp: new Date(Date.now() - 14400000).toISOString(),
    action: 'DAILY_LIMIT_CHECK', actor: 'POLICY_ENGINE', description: 'Daily email limit: 1/3',
    resource_type: 'policy', resource_id: 'policy_daily_limit', result: 'allowed',
    policy_name: 'MAX_EMAILS_PER_DAY', payload: { sent_today: 1, limit: 3 },
  },
  {
    id: 'aud_013', timestamp: new Date(Date.now() - 18000000).toISOString(),
    action: 'WEBHOOK_RECEIVED', actor: 'SYSTEM', description: 'Razorpay webhook: payment.captured',
    resource_type: 'webhook', resource_id: 'wh_001', result: 'success',
    policy_name: null, payload: { event: 'payment.captured', order_id: 'order_9c1f5e8b' },
  },
  {
    id: 'aud_014', timestamp: new Date(Date.now() - 21600000).toISOString(),
    action: 'AGENT_STARTED', actor: 'AI_AGENT', description: 'Agent workflow initiated for payment failure',
    resource_type: 'agent_run', resource_id: 'run_003', result: 'success',
    policy_name: null, payload: { stage: 'OBSERVE' },
  },
  {
    id: 'aud_015', timestamp: new Date(Date.now() - 25200000).toISOString(),
    action: 'PAYMENT_FAILED', actor: 'SYSTEM', description: 'Payment failed: bank_declined',
    resource_type: 'payment', resource_id: 'pay_9c1f5e8b', result: 'success',
    policy_name: null, payload: { failure_code: 'BANK_DECLINED' },
  },
  {
    id: 'aud_016', timestamp: new Date(Date.now() - 28800000).toISOString(),
    action: 'HUMAN_REVIEW_ESCALATED', actor: 'POLICY_ENGINE', description: 'High-risk payment escalated for human review',
    resource_type: 'payment', resource_id: 'pay_a8c3e1d5', result: 'blocked',
    policy_name: 'HUMAN_REVIEW_THRESHOLD', payload: { amount: 99900 },
  },
  {
    id: 'aud_017', timestamp: new Date(Date.now() - 36000000).toISOString(),
    action: 'RECOVERY_EMAIL_OPENED', actor: 'EMAIL_SERVICE', description: 'Customer opened recovery email',
    resource_type: 'email_message', resource_id: 'msg_002', result: 'success',
    policy_name: null, payload: { opened_at: new Date(Date.now() - 33000000).toISOString() },
  },
  {
    id: 'aud_018', timestamp: new Date(Date.now() - 43200000).toISOString(),
    action: 'PAYMENT_LINK_CLICKED', actor: 'SYSTEM', description: 'Customer clicked recovery payment link',
    resource_type: 'payment_link', resource_id: 'link_001', result: 'success',
    policy_name: null, payload: { payment_id: 'pay_7f82a91c' },
  },
  {
    id: 'aud_019', timestamp: new Date(Date.now() - 50400000).toISOString(),
    action: 'SYSTEM_HEALTH_CHECK', actor: 'SYSTEM', description: 'All services operational',
    resource_type: 'system', resource_id: 'health', result: 'success',
    policy_name: null, payload: { webhook: 'healthy', worker: 'healthy', agent: 'healthy', email: 'healthy' },
  },
  {
    id: 'aud_020', timestamp: new Date(Date.now() - 86400000).toISOString(),
    action: 'POLICY_UPDATED', actor: 'MERCHANT', description: 'Maximum auto payment updated from ₹4,000 to ₹5,000',
    resource_type: 'policy', resource_id: 'policy_max_auto', result: 'success',
    policy_name: 'MAX_AUTO_PAYMENT', payload: { old_value: 400000, new_value: 500000 },
  },
]
