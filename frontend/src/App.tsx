import { useState } from 'react'
import './App.css'

type FailureType = 'upi_timeout' | 'bank_declined' | 'insufficient_funds' | 'network_error' | 'gateway_error' | 'fraud_check'

interface SimulateResult {
  status: string
  customer_id: string
  customer_email: string
  payment_id: string
  razorpay_order_id: string
  razorpay_payment_id: string
  amount: number
  currency: string
  failure_type: string
  failure_code: string
  failure_reason: string
  email_sent_to: string
  recovery_pipeline: string
  message: string
}

const FAILURE_TYPES: { value: FailureType; label: string; description: string }[] = [
  { value: 'upi_timeout', label: 'UPI Timeout', description: 'UPI session timed out' },
  { value: 'bank_declined', label: 'Bank Declined', description: 'Card declined by issuing bank' },
  { value: 'insufficient_funds', label: 'Insufficient Funds', description: 'Not enough money in account' },
  { value: 'network_error', label: 'Network Error', description: 'Connection lost during payment' },
  { value: 'gateway_error', label: 'Gateway Error', description: 'Payment gateway unavailable' },
  { value: 'fraud_check', label: 'Fraud Check', description: 'Transaction flagged for review' },
]

function App() {
  const [failureType, setFailureType] = useState<FailureType>('upi_timeout')
  const [email, setEmail] = useState('test@example.com')
  const [amount, setAmount] = useState(49900)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SimulateResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSimulate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch('/api/simulate/failure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_email: email,
          customer_name: 'Test Customer',
          amount,
          failure_type: failureType,
        }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Simulation failed')
      }

      const data: SimulateResult = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 640, margin: '2rem auto', fontFamily: 'system-ui, sans-serif', padding: '0 1rem' }}>
      <h1>RecoverFlow — Simulate Payment Failure</h1>
      <p style={{ color: '#666' }}>
        Generate a realistic failed payment that triggers the full recovery pipeline.
      </p>

      <div style={{ padding: '10px 14px', background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: 6, fontSize: 13, color: '#92400e', marginTop: '1rem' }}>
        <strong>Dev Mode:</strong> Recovery emails are redirected to your verified email. The <code>email_sent_to</code> field in the response shows where the email actually goes.
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Customer Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', border: '1px solid #ccc', borderRadius: 6 }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Amount (paise)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            style={{ width: '100%', padding: '8px 12px', border: '1px solid #ccc', borderRadius: 6 }}
          />
          <span style={{ color: '#888', fontSize: 13 }}> = ₹{(amount / 100).toFixed(2)}</span>
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: 4 }}>Failure Type</label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {FAILURE_TYPES.map((ft) => (
              <button
                key={ft.value}
                onClick={() => setFailureType(ft.value)}
                style={{
                  padding: '10px 12px',
                  border: failureType === ft.value ? '2px solid #e53e3e' : '1px solid #ccc',
                  borderRadius: 6,
                  background: failureType === ft.value ? '#fff5f5' : '#fff',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 14 }}>{ft.label}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{ft.description}</div>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleSimulate}
          disabled={loading}
          style={{
            padding: '12px 24px',
            background: '#e53e3e',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 16,
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Simulating...' : 'Simulate Payment Failure'}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: '1.5rem', padding: 12, background: '#fed7d7', borderRadius: 6, color: '#c53030' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: '1.5rem', padding: 16, background: '#f0fff4', border: '1px solid #c6f6d5', borderRadius: 6 }}>
          <h3 style={{ margin: '0 0 8px', color: '#276749' }}>Failure Simulated</h3>
          <p style={{ margin: 0, color: '#276749' }}>{result.message}</p>
          <table style={{ width: '100%', marginTop: 12, fontSize: 13, borderCollapse: 'collapse' }}>
            <tbody>
              {[
                ['Customer', result.customer_email],
                ['Order ID', result.razorpay_order_id],
                ['Payment ID', result.razorpay_payment_id],
                ['Amount', `₹${(result.amount / 100).toFixed(2)}`],
                ['Failure Code', result.failure_code],
                ['Failure Reason', result.failure_reason],
                ['Payment Status', result.status],
                ['Email Sent To', result.email_sent_to],
                ['Recovery Pipeline', result.recovery_pipeline],
              ].map(([label, value]) => (
                <tr key={String(label)}>
                  <td style={{ padding: '4px 8px 4px 0', fontWeight: 600, whiteSpace: 'nowrap' }}>{label}</td>
                  <td style={{ padding: '4px 0', fontFamily: 'monospace', fontSize: 12 }}>{String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default App
