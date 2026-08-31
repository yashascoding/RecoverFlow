import { api } from './client'

export interface OverviewMetrics {
  total_revenue: number
  revenue_at_risk: number
  recovered_revenue: number
  failed_payments: number
  recovery_rate: number
  total_payments: number
  previous_period_revenue: number
  previous_period_recovered: number
  previous_period_failed: number
}

export interface ActivityItem {
  id: string
  customer: string
  amount: number
  status: string
  time: string
}

export interface HealthService {
  name: string
  status: string
  latency_ms: number
}

export async function getOverview(): Promise<OverviewMetrics> {
  return api.get<OverviewMetrics>('/api/payments/stats/overview')
}

export async function getRecentActivity(): Promise<ActivityItem[]> {
  return api.get<ActivityItem[]>('/api/payments/recent-activity')
}

interface HealthResponse {
  status: string
  postgres: string
  redis: string
  timestamp: string
}

export async function getSystemHealth(): Promise<HealthService[]> {
  const res = await api.get<HealthResponse>('/api/health')
  return [
    { name: 'PostgreSQL', status: res.postgres, latency_ms: 0 },
    { name: 'Redis', status: res.redis, latency_ms: 0 },
  ]
}
