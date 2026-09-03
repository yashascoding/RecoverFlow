import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import {
  getInvestigations,
  getTopContributors,
  generateDiagnosis,
  createSyntheticUPIDegradation,
  createSyntheticBankDeclineSpike,
  createSyntheticGatewayTimeout,
  runAllSyntheticTests,
} from '@/api/investigations'
import { formatRelativeTime } from '@/lib/utils'
import {
  Search,
  Brain,
  Target,
  Activity,
  Zap,
  AlertTriangle,
  TrendingDown,
} from 'lucide-react'

export function InvestigationsPage() {
  const navigate = useNavigate()
  const [syntheticRunning, setSyntheticRunning] = useState(false)
  const [lastSyntheticRun, setLastSyntheticRun] = useState<string | null>(null)

  const { data: investigations, loading: investigationsLoading, refetch: refetchInvestigations } = useApi(
    () => getInvestigations(undefined, undefined, undefined, 1, 10)
  )

  const { data: topContributors, loading: contributorsLoading } = useApi(
    () => getTopContributors(24, 5)
  )

  const { data: diagnosis, loading: diagnosisLoading } = useApi(
    () => generateDiagnosis(24)
  )

  const handleRunAllSynthetic = async () => {
    setSyntheticRunning(true)
    try {
      await runAllSyntheticTests()
      setLastSyntheticRun(new Date().toISOString())
      await refetchInvestigations()
    } catch (error) {
      console.error('Synthetic test failed:', error)
    } finally {
      setSyntheticRunning(false)
    }
  }

  const handleCreateSynthetic = async (type: string) => {
    setSyntheticRunning(true)
    try {
      switch (type) {
        case 'upi':
          await createSyntheticUPIDegradation()
          break
        case 'bank':
          await createSyntheticBankDeclineSpike()
          break
        case 'gateway':
          await createSyntheticGatewayTimeout()
          break
      }
      setLastSyntheticRun(new Date().toISOString())
      await refetchInvestigations()
    } catch (error) {
      console.error('Synthetic creation failed:', error)
    } finally {
      setSyntheticRunning(false)
    }
  }

  return (
    <PageContainer
      title="Investigations"
      description="Investigation state machine and root cause analysis"
    >
      {/* Investigation State Machine */}
      <div className="rounded-lg border border-border bg-card p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-md bg-recovery/10 flex items-center justify-center">
            <Search className="w-4 h-4 text-recovery" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Investigation Pipeline</h3>
            <p className="text-[12px] text-muted-foreground">OBSERVE → QUERY → CORRELATE → DIAGNOSE</p>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[
            { state: 'OBSERVE', desc: 'Monitor metrics and detect anomalies', icon: Activity },
            { state: 'QUERY', desc: 'Query failure data across dimensions', icon: Search },
            { state: 'CORRELATE', desc: 'Identify and rank contributors', icon: Target },
            { state: 'DIAGNOSE', desc: 'Generate AI-powered diagnosis', icon: Brain },
          ].map((step, idx) => (
            <div key={idx} className="relative">
              <div className="rounded-md bg-secondary/50 border border-border p-3 h-full">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-[10px] font-mono text-muted-foreground">0{idx + 1}</span>
                  <step.icon className="w-3.5 h-3.5 text-recovery" />
                </div>
                <p className="text-[12px] font-medium text-foreground">{step.state}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">{step.desc}</p>
              </div>
              {idx < 3 && (
                <div className="hidden lg:block absolute top-1/2 -right-1.5 w-3 h-px bg-border" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {investigationsLoading || contributorsLoading || diagnosisLoading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : (
          <>
            <MetricCard
              title="Active Investigations"
              value={investigations ? investigations.total.toString() : '0'}
              description="In progress"
              icon={<Search className="w-4 h-4" />}
            />
            <MetricCard
              title="Top Contributor"
              value={topContributors && topContributors.length > 0 ? topContributors[0].value : 'N/A'}
              description={topContributors && topContributors.length > 0 ? topContributors[0].dimension : 'No data'}
              icon={<Target className="w-4 h-4" />}
            />
            <MetricCard
              title="Diagnosis Confidence"
              value={diagnosis ? `${(diagnosis.confidence * 100).toFixed(0)}%` : 'N/A'}
              description={diagnosis ? diagnosis.contributor_dimension : 'No diagnosis'}
              icon={<Brain className="w-4 h-4" />}
            />
            <MetricCard
              title="Synthetic Tests"
              value={lastSyntheticRun ? '1' : '0'}
              description={lastSyntheticRun ? `Last: ${formatRelativeTime(lastSyntheticRun)}` : 'Not run yet'}
              icon={<Zap className="w-4 h-4" />}
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Top Contributors */}
        <div className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Top Contributors
            </p>
          </div>
          <div className="divide-y divide-border">
            {contributorsLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="px-4 py-3 space-y-2">
                  <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                  <div className="h-3 w-48 bg-secondary animate-pulse rounded" />
                </div>
              ))
            ) : topContributors && topContributors.length > 0 ? (
              topContributors.map((contributor, idx) => (
                <div key={idx} className="px-4 py-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-muted-foreground">#{contributor.rank}</span>
                      <span className="text-[13px] font-medium text-foreground">{contributor.value}</span>
                    </div>
                    <span className="text-[12px] text-recovery font-mono">
                      {(contributor.contribution_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-[11px] text-muted-foreground">{contributor.dimension}</span>
                    <span className="text-[11px] text-muted-foreground">
                      Confidence: {(contributor.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-8 text-center">
                <p className="text-[13px] text-muted-foreground">No contributors detected</p>
              </div>
            )}
          </div>
        </div>

        {/* Diagnosis */}
        <div className="rounded-lg border border-border bg-card">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              AI Diagnosis
            </p>
          </div>
          <div className="p-4">
            {diagnosisLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-6 bg-secondary animate-pulse rounded" />
                ))}
              </div>
            ) : diagnosis ? (
              <div className="space-y-4">
                <div className="rounded-md bg-secondary/50 border border-border p-4">
                  <p className="text-[13px] text-foreground font-medium mb-2">Summary</p>
                  <p className="text-[12px] text-muted-foreground">{diagnosis.summary}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-md bg-secondary/50 border border-border p-3">
                    <p className="text-[11px] text-muted-foreground mb-1">Primary Contributor</p>
                    <p className="text-[13px] font-medium text-foreground">{diagnosis.primary_contributor}</p>
                  </div>
                  <div className="rounded-md bg-secondary/50 border border-border p-3">
                    <p className="text-[11px] text-muted-foreground mb-1">Affected Region</p>
                    <p className="text-[13px] font-medium text-foreground">{diagnosis.affected_region || 'N/A'}</p>
                  </div>
                  <div className="rounded-md bg-secondary/50 border border-border p-3">
                    <p className="text-[11px] text-muted-foreground mb-1">Confidence</p>
                    <p className="text-[13px] font-medium text-recovery">
                      {(diagnosis.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="rounded-md bg-secondary/50 border border-border p-3">
                    <p className="text-[11px] text-muted-foreground mb-1">Dimension</p>
                    <p className="text-[13px] font-medium text-foreground">{diagnosis.contributor_dimension}</p>
                  </div>
                </div>
                <div className="rounded-md bg-secondary/50 border border-border p-4">
                  <p className="text-[11px] text-muted-foreground mb-1">Recommendation</p>
                  <p className="text-[12px] text-foreground">{diagnosis.recommendation}</p>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-[13px] text-muted-foreground">No diagnosis available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Synthetic Incident Testing */}
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-orange-500/10 flex items-center justify-center">
              <Zap className="w-4 h-4 text-orange-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Synthetic Incident Testing</h3>
              <p className="text-[12px] text-muted-foreground">Create test incidents to validate investigation pipeline</p>
            </div>
          </div>
          <button
            onClick={handleRunAllSynthetic}
            disabled={syntheticRunning}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-recovery text-white text-[13px] font-medium hover:bg-recovery/90 transition-colors disabled:opacity-50"
          >
            <Zap className={`w-4 h-4 ${syntheticRunning ? 'animate-spin' : ''}`} />
            {syntheticRunning ? 'Running...' : 'Run All Tests'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-md bg-secondary/50 border border-border p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-blue-400" />
              <p className="text-[13px] font-medium text-foreground">UPI Degradation</p>
            </div>
            <p className="text-[11px] text-muted-foreground mb-3">
              Simulate UPI payment failures across multiple banks
            </p>
            <button
              onClick={() => handleCreateSynthetic('upi')}
              disabled={syntheticRunning}
              className="w-full px-3 py-1.5 rounded-md bg-blue-500/10 text-blue-400 text-[12px] font-medium hover:bg-blue-500/20 transition-colors disabled:opacity-50"
            >
              Create Test
            </button>
          </div>

          <div className="rounded-md bg-secondary/50 border border-border p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-orange-400" />
              <p className="text-[13px] font-medium text-foreground">Bank Decline Spike</p>
            </div>
            <p className="text-[11px] text-muted-foreground mb-3">
              Simulate spike in bank card declines
            </p>
            <button
              onClick={() => handleCreateSynthetic('bank')}
              disabled={syntheticRunning}
              className="w-full px-3 py-1.5 rounded-md bg-orange-500/10 text-orange-400 text-[12px] font-medium hover:bg-orange-500/20 transition-colors disabled:opacity-50"
            >
              Create Test
            </button>
          </div>

          <div className="rounded-md bg-secondary/50 border border-border p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <p className="text-[13px] font-medium text-foreground">Gateway Timeout</p>
            </div>
            <p className="text-[11px] text-muted-foreground mb-3">
              Simulate payment gateway timeout issues
            </p>
            <button
              onClick={() => handleCreateSynthetic('gateway')}
              disabled={syntheticRunning}
              className="w-full px-3 py-1.5 rounded-md bg-red-500/10 text-red-400 text-[12px] font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50"
            >
              Create Test
            </button>
          </div>
        </div>

        {lastSyntheticRun && (
          <div className="mt-4 p-3 rounded-md bg-success/10 border border-success/20">
            <p className="text-[12px] text-success">
              Last synthetic test run: {formatRelativeTime(lastSyntheticRun)}
            </p>
          </div>
        )}
      </div>

      {/* Recent Investigations */}
      <div className="rounded-lg border border-border bg-card mt-6">
        <div className="px-4 py-3 border-b border-border">
          <div className="flex items-center justify-between">
            <p className="text-[12px] font-medium text-muted-foreground uppercase tracking-wider">
              Recent Investigations
            </p>
            <button
              onClick={() => refetchInvestigations()}
              className="text-[12px] text-recovery hover:underline"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="divide-y divide-border">
          {investigationsLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="px-4 py-3 space-y-2">
                <div className="h-3 w-32 bg-secondary animate-pulse rounded" />
                <div className="h-3 w-48 bg-secondary animate-pulse rounded" />
              </div>
            ))
          ) : investigations && investigations.items.length > 0 ? (
            investigations.items.map((investigation) => (
              <div
                key={investigation.id}
                className="px-4 py-3 cursor-pointer hover:bg-secondary/30 transition-colors"
                onClick={() => navigate(`/investigations/${investigation.id}`)}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[13px] font-medium text-foreground">{investigation.title}</span>
                  <StatusBadge status={investigation.state} />
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-[11px] text-muted-foreground">
                    {formatRelativeTime(investigation.created_at)}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Status: {investigation.status}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="px-4 py-8 text-center">
              <p className="text-[13px] text-muted-foreground">No investigations yet</p>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
