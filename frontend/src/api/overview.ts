import { overviewMetrics, recoveryRateData, failedPaymentsData, recoveredRevenueData, revenueAtRiskData, recentActivity, systemHealth } from '@/mocks/overview'

export async function getOverview() {
  return overviewMetrics
}

export async function getRecoveryRateChart() {
  return recoveryRateData
}

export async function getFailedPaymentsChart() {
  return failedPaymentsData
}

export async function getRecoveredRevenueChart() {
  return recoveredRevenueData
}

export async function getRevenueAtRiskChart() {
  return revenueAtRiskData
}

export async function getRecentActivity() {
  return recentActivity
}

export async function getSystemHealth() {
  return systemHealth
}
