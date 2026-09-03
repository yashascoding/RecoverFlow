import { api } from './client'

export interface TransactionMetrics {
  total_transactions: number
  successful_transactions: number
  failed_transactions: number
  success_rate: number
  failure_rate: number
  revenue_at_risk: number
  recovered_revenue: number
  total_revenue: number
  recovery_rate: number
}

export interface TimeSeriesPoint {
  timestamp: string
  success_rate: number
  failure_rate: number
  revenue_at_risk: number
  recovered_revenue: number
  total_transactions: number
}

export interface TransactionMonitoringResponse {
  metrics: TransactionMetrics
  time_series: TimeSeriesPoint[]
  period_start: string
  period_end: string
}

export interface FailureGroup {
  group_name: string
  group_value: string
  failure_count: number
  revenue_at_risk: number
  percentage: number
  top_failure_reasons: string[]
}

export interface FailureAnalysisResponse {
  total_failures: number
  revenue_at_risk: number
  groups: FailureGroup[]
  period_start: string
  period_end: string
  group_by: string
}

export interface FailureSummary {
  total_failures: number
  revenue_at_risk: number
  by_failure_reason: Array<{ name: string; count: number; revenue_at_risk: number }>
  by_gateway: Array<{ name: string; count: number; revenue_at_risk: number }>
  by_bank: Array<{ name: string; count: number; revenue_at_risk: number }>
  by_region: Array<{ name: string; count: number; revenue_at_risk: number }>
  by_payment_method: Array<{ name: string; count: number; revenue_at_risk: number }>
}

export async function getTransactionMonitoring(
  timeWindowHours: number = 24,
  granularity: string = 'hourly'
): Promise<TransactionMonitoringResponse> {
  return api.get<TransactionMonitoringResponse>(
    `/api/monitoring/transactions?time_window_hours=${timeWindowHours}&granularity=${granularity}`
  )
}

export async function getTransactionSummary(
  timeWindowHours: number = 24
): Promise<TransactionMetrics> {
  return api.get<TransactionMetrics>(
    `/api/monitoring/transactions/summary?time_window_hours=${timeWindowHours}`
  )
}

export async function getFailureAnalysis(
  timeWindowHours: number = 24,
  groupBy: string = 'failure_reason'
): Promise<FailureAnalysisResponse> {
  return api.get<FailureAnalysisResponse>(
    `/api/monitoring/failures?time_window_hours=${timeWindowHours}&group_by=${groupBy}`
  )
}

export async function getFailureSummary(
  timeWindowHours: number = 24
): Promise<FailureSummary> {
  return api.get<FailureSummary>(
    `/api/monitoring/failures/summary?time_window_hours=${timeWindowHours}`
  )
}

export interface SpikeAlert {
  spike_type: string
  dimension: string
  current_count: number
  baseline_count: number
  threshold: number
  severity: string
  revenue_impact: number
  detected_at: string
  message: string
}

export interface SpikeDetectionResponse {
  spikes_detected: boolean
  spike_count: number
  spikes: SpikeAlert[]
  period_start: string
  period_end: string
  baseline_period_start: string
  baseline_period_end: string
}

export interface DegradationMetric {
  dimension: string
  current_failure_rate: number
  previous_failure_rate: number
  change_percentage: number
  is_degraded: boolean
  revenue_impact: number
}

export async function detectSpikes(
  timeWindowHours: number = 24,
  thresholdMultiplier: number = 2.0
): Promise<SpikeDetectionResponse> {
  return api.get<SpikeDetectionResponse>(
    `/api/monitoring/spikes?time_window_hours=${timeWindowHours}&threshold_multiplier=${thresholdMultiplier}`
  )
}

export async function detectDegradation(
  timeWindowHours: number = 24
): Promise<DegradationMetric[]> {
  return api.get<DegradationMetric[]>(
    `/api/monitoring/degradation?time_window_hours=${timeWindowHours}`
  )
}
