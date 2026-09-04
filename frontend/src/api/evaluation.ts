import { api } from './client'
import type { EvaluationDashboardResponse } from '@/types'

export async function getEvaluationDashboard(
  timeWindowHours: number = 168
): Promise<EvaluationDashboardResponse> {
  return api.get<EvaluationDashboardResponse>(
    `/api/evaluation/dashboard?time_window_hours=${timeWindowHours}`
  )
}

export async function runEvaluation(
  timeWindowHours: number = 168
): Promise<EvaluationDashboardResponse> {
  return api.post<EvaluationDashboardResponse>('/api/evaluation/run', {
    time_window_hours: timeWindowHours,
  })
}

export async function assignControlGroup(
  controlPercentage: number = 10
): Promise<{ total_assigned: number; control_count: number; ai_count: number; control_percentage: number }> {
  return api.post('/api/evaluation/control-group/assign', {
    control_percentage: controlPercentage,
  })
}
