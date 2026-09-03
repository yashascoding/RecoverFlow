import { api } from './client'

interface SentinelResult {
  alerts_checked: number
  alerts_triggered: number
  incidents_created: number
  investigations_started: number
  details: Array<{
    alert_id?: string
    alert_name?: string
    metric_value?: number
    threshold?: number
    incident_created?: boolean
    message: string
    error?: string
    spike_type?: string
    dimension?: string
    severity?: string
  }>
}

interface SentinelStatus {
  status: string
  active_alerts: number
  open_incidents: number
  investigating_incidents: number
  total_revenue_at_risk: number
}

export async function runSentinelCheck(): Promise<SentinelResult> {
  return api.post<SentinelResult>('/api/sentinel/run')
}

export async function getSentinelStatus(): Promise<SentinelStatus> {
  return api.get<SentinelStatus>('/api/sentinel/status')
}
