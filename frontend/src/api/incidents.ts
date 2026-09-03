import { api } from './client'
import type { Incident } from '@/types'

interface IncidentCreate {
  title: string
  description?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  incident_type: string
  affected_gateway?: string
  affected_bank?: string
  affected_region?: string
  affected_payment_method?: string
  failure_reason?: string
  revenue_at_risk: number
  failure_count: number
  baseline_failure_count: number
  spike_threshold: number
  detected_at: string
  metadata_?: Record<string, unknown>
}

interface IncidentUpdate {
  status?: 'open' | 'investigating' | 'resolved' | 'escalated'
  severity?: 'low' | 'medium' | 'high' | 'critical'
  description?: string
  resolved_at?: string
  metadata_?: Record<string, unknown>
}

interface IncidentStats {
  total_incidents: number
  open_incidents: number
  investigating_incidents: number
  resolved_incidents: number
  escalated_incidents: number
  total_revenue_at_risk: number
  by_severity: Record<string, number>
  by_type: Record<string, number>
}

export async function createIncident(data: IncidentCreate): Promise<Incident> {
  return api.post<Incident>('/api/incidents/', data)
}

export async function getIncidents(
  status?: string,
  severity?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: Incident[]; total: number; page: number; page_size: number; pages: number }> {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  if (severity) params.append('severity', severity)
  params.append('page', page.toString())
  params.append('page_size', pageSize.toString())
  return api.get(`/api/incidents/?${params.toString()}`)
}

export async function getIncident(id: string): Promise<Incident> {
  return api.get<Incident>(`/api/incidents/${id}`)
}

export async function updateIncident(id: string, data: IncidentUpdate): Promise<Incident> {
  return api.patch<Incident>(`/api/incidents/${id}`, data)
}

export async function getIncidentStats(): Promise<IncidentStats> {
  return api.get<IncidentStats>('/api/incidents/stats')
}
