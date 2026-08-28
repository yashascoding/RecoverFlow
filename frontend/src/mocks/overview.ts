import type { OverviewMetrics, ChartDataPoint } from '@/types'

const now = new Date()

export const overviewMetrics: OverviewMetrics = {
  total_revenue: 12400000,
  revenue_at_risk: 385200,
  recovered_revenue: 964200,
  failed_payments: 47,
  recovery_rate: 72.3,
  total_payments: 1842,
  previous_period_revenue: 11440000,
  previous_period_recovered: 813500,
  previous_period_failed: 53,
}

function generateDailyData(days: number, baseValue: number, variance: number): ChartDataPoint[] {
  return Array.from({ length: days }, (_, i) => {
    const date = new Date(now)
    date.setDate(date.getDate() - (days - 1 - i))
    return {
      date: date.toISOString().split('T')[0],
      value: Math.round(baseValue + (Math.random() - 0.3) * variance),
    }
  })
}

export const recoveryRateData = generateDailyData(30, 68, 20)
export const failedPaymentsData = generateDailyData(30, 5, 8)
export const recoveredRevenueData = generateDailyData(30, 350000, 200000)
export const revenueAtRiskData = generateDailyData(30, 150000, 100000)

export const recentActivity = [
  { id: 'pay_7f82a91c', customer: 'Rahul Sharma', amount: 249900, status: 'recovered', time: new Date(now.getTime() - 2 * 60000).toISOString() },
  { id: 'pay_3b4e7d2a', customer: 'Priya Patel', amount: 420000, status: 'recovery_pending', time: new Date(now.getTime() - 5 * 60000).toISOString() },
  { id: 'pay_9c1f5e8b', customer: 'Amit Kumar', amount: 159900, status: 'recovered', time: new Date(now.getTime() - 12 * 60000).toISOString() },
  { id: 'pay_2d6a8c4f', customer: 'Sneha Reddy', amount: 89900, status: 'failed', time: new Date(now.getTime() - 18 * 60000).toISOString() },
  { id: 'pay_5e3b7a1d', customer: 'Vikram Singh', amount: 349900, status: 'recovered', time: new Date(now.getTime() - 25 * 60000).toISOString() },
]

export const systemHealth = [
  { name: 'Webhook Processor', status: 'healthy' as const, latency_ms: 12 },
  { name: 'Recovery Worker', status: 'healthy' as const, latency_ms: 45 },
  { name: 'AI Agent', status: 'healthy' as const, latency_ms: 890 },
  { name: 'Email Service', status: 'healthy' as const, latency_ms: 230 },
]
