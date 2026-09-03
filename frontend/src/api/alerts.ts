import { api } from './client'

interface Alert {
  id: string
  name: string
  description: string | null
  status: string
  severity: string
  alert_type: string
  metric_name: string
  threshold_value: number
  comparison_operator: string
  time_window_minutes: number
  cooldown_minutes: number
  last_triggered_at: string | null
  last_value: number | null
  incident_id: string | null
  metadata_: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

interface AlertCreate {
  name: string
  description?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  alert_type: string
  metric_name: string
  threshold_value: number
  comparison_operator: 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
  time_window_minutes: number
  cooldown_minutes: number
  metadata_?: Record<string, unknown>
}

interface AlertUpdate {
  name?: string
  description?: string
  status?: 'active' | 'triggered' | 'resolved' | 'disabled'
  severity?: 'low' | 'medium' | 'high' | 'critical'
  threshold_value?: number
  comparison_operator?: 'gt' | 'gte' | 'lt' | 'lte' | 'eq'
  time_window_minutes?: number
  cooldown_minutes?: number
  metadata_?: Record<string, unknown>
}

interface AlertTestRequest {
  metric_value: number
  alert_id?: string
}

interface AlertTestResponse {
  would_trigger: boolean
  current_value: number
  threshold_value: number
  comparison_operator: string
  alert_name: string
  message: string
}

export async function createAlert(data: AlertCreate): Promise<Alert> {
  return api.post<Alert>('/api/alerts/', data)
}

export async function getAlerts(
  status?: string,
  severity?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: Alert[]; total: number; page: number; page_size: number; pages: number }> {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  if (severity) params.append('severity', severity)
  params.append('page', page.toString())
  params.append('page_size', pageSize.toString())
  return api.get(`/api/alerts/?${params.toString()}`)
}

export async function getAlert(id: string): Promise<Alert> {
  return api.get<Alert>(`/api/alerts/${id}`)
}

export async function updateAlert(id: string, data: AlertUpdate): Promise<Alert> {
  return api.patch<Alert>(`/api/alerts/${id}`, data)
}

export async function testAlert(data: AlertTestRequest): Promise<AlertTestResponse> {
  return api.post<AlertTestResponse>('/api/alerts/test', data)
}
