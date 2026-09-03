import { api } from './client'

export interface Investigation {
  id: string
  incident_id: string
  payment_id: string | null
  state: string
  status: string
  title: string
  description: string | null
  query_results: Record<string, unknown> | null
  correlation_results: Record<string, unknown> | null
  diagnosis: Record<string, unknown> | null
  started_at: string | null
  completed_at: string | null
  metadata_: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface InvestigationCreate {
  incident_id: string
  payment_id?: string
  title: string
  description?: string
  metadata_?: Record<string, unknown>
}

export interface InvestigationUpdate {
  state?: string
  status?: string
  description?: string
  query_results?: Record<string, unknown>
  correlation_results?: Record<string, unknown>
  diagnosis?: Record<string, unknown>
  metadata_?: Record<string, unknown>
}

export interface QueryResult {
  dimension: string
  value: string
  count: number
  revenue_impact: number
  percentage: number
}

export interface CorrelationResult {
  dimension: string
  value: string
  contribution_score: number
  confidence: number
  rank: number
}

export interface DiagnosisOutput {
  primary_contributor: string
  contributor_dimension: string
  affected_region: string | null
  failure_pattern: string
  confidence: number
  summary: string
  recommendation: string
}

export interface RecoveryStrategy {
  strategy_name: string
  description: string
  actions: Array<{
    action: string
    description: string
    priority: string
  }>
  estimated_recovery_rate: number
  priority: string
  timeline: string
  resources_required: string[]
}

export async function createInvestigation(data: InvestigationCreate): Promise<Investigation> {
  return api.post<Investigation>('/api/investigations/', data)
}

export async function getInvestigations(
  incidentId?: string,
  state?: string,
  status?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<{ items: Investigation[]; total: number; page: number; page_size: number; pages: number }> {
  const params = new URLSearchParams()
  if (incidentId) params.append('incident_id', incidentId)
  if (state) params.append('state', state)
  if (status) params.append('status', status)
  params.append('page', page.toString())
  params.append('page_size', pageSize.toString())
  return api.get(`/api/investigations/?${params.toString()}`)
}

export async function getInvestigation(id: string): Promise<Investigation> {
  return api.get<Investigation>(`/api/investigations/${id}`)
}

export async function updateInvestigation(id: string, data: InvestigationUpdate): Promise<Investigation> {
  return api.patch<Investigation>(`/api/investigations/${id}`, data)
}

export async function transitionInvestigation(
  id: string,
  targetState: string,
  data?: Record<string, unknown>
): Promise<Investigation> {
  return api.post<Investigation>(`/api/investigations/${id}/transition/${targetState}`, data)
}

export async function queryByDimension(
  dimension: string,
  timeWindowHours: number = 24
): Promise<QueryResult[]> {
  return api.get<QueryResult[]>(
    `/api/investigations/queries/${dimension}?time_window_hours=${timeWindowHours}`
  )
}

export async function queryAllDimensions(
  timeWindowHours: number = 24
): Promise<Record<string, QueryResult[]>> {
  return api.get<Record<string, QueryResult[]>>(
    `/api/investigations/queries/all?time_window_hours=${timeWindowHours}`
  )
}

export async function queryFailurePattern(
  timeWindowHours: number = 24
): Promise<Record<string, unknown>> {
  return api.get<Record<string, unknown>>(
    `/api/investigations/queries/pattern?time_window_hours=${timeWindowHours}`
  )
}

export async function analyzeCorrelations(
  timeWindowHours: number = 24
): Promise<CorrelationResult[]> {
  return api.get<CorrelationResult[]>(
    `/api/investigations/correlations?time_window_hours=${timeWindowHours}`
  )
}

export async function getTopContributors(
  timeWindowHours: number = 24,
  limit: number = 5
): Promise<CorrelationResult[]> {
  return api.get<CorrelationResult[]>(
    `/api/investigations/correlations/top?time_window_hours=${timeWindowHours}&limit=${limit}`
  )
}

export async function generateDiagnosis(
  timeWindowHours: number = 24
): Promise<DiagnosisOutput> {
  return api.get<DiagnosisOutput>(
    `/api/investigations/diagnosis?time_window_hours=${timeWindowHours}`
  )
}

export async function generateRecoveryStrategy(
  diagnosis: DiagnosisOutput,
  correlationResults?: CorrelationResult[]
): Promise<RecoveryStrategy> {
  return api.post<RecoveryStrategy>('/api/investigations/strategy', {
    diagnosis,
    correlation_results: correlationResults,
  })
}

export async function createSyntheticUPIDegradation(
  affectedCount: number = 50,
  revenueImpact: number = 2500000
): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(
    `/api/investigations/synthetic/upi-degradation?affected_count=${affectedCount}&revenue_impact=${revenueImpact}`
  )
}

export async function createSyntheticBankDeclineSpike(
  affectedBank: string = 'HDFC',
  affectedCount: number = 75,
  revenueImpact: number = 3750000
): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(
    `/api/investigations/synthetic/bank-decline-spike?affected_bank=${affectedBank}&affected_count=${affectedCount}&revenue_impact=${revenueImpact}`
  )
}

export async function createSyntheticGatewayTimeout(
  affectedGateway: string = 'Razorpay',
  affectedCount: number = 100,
  revenueImpact: number = 5000000
): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>(
    `/api/investigations/synthetic/gateway-timeout?affected_gateway=${affectedGateway}&affected_count=${affectedCount}&revenue_impact=${revenueImpact}`
  )
}

export async function runAllSyntheticTests(): Promise<Record<string, unknown>> {
  return api.post<Record<string, unknown>>('/api/investigations/synthetic/run-all')
}
