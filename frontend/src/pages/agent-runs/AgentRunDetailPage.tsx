import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Clock, Wrench } from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { useApi } from '@/hooks/useApi'
import { getAgentRun } from '@/api/agentRuns'
import { useState } from 'react'

interface ToolCall {
  tool_name: string
  latency_ms: number
  result?: Record<string, unknown>
  error?: string | null
  arguments?: Record<string, unknown>
}

export function AgentRunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: run, loading } = useApi(() => getAgentRun(id!), [id])
  const [expandedStage, setExpandedStage] = useState<string | null>(null)

  if (loading) {
    return (
      <PageContainer title="Agent Trace">
        <div className="h-96 bg-secondary animate-pulse rounded-lg" />
      </PageContainer>
    )
  }

  if (!run) {
    return (
      <PageContainer title="Agent Trace">
        <div className="text-center py-12">
          <p className="text-muted-foreground">Agent run not found</p>
          <Link to="/agent-runs" className="text-sm text-recovery hover:underline mt-2 inline-block">Back to Agent Runs</Link>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="Agent Trace" description={`Run ${run.id} — ${run.diagnosis}`}>
      <Link to="/agent-runs" className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Agent Runs
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Diagnosis</p>
          <p className="text-sm font-mono font-medium text-foreground mt-1">{run.diagnosis}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Confidence</p>
          <p className="text-sm font-mono font-medium text-foreground mt-1">{(run.confidence * 100).toFixed(0)}%</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Decision</p>
          <p className="text-sm font-mono font-medium text-foreground mt-1">{run.decision}</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-3">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Duration</p>
          <p className="text-sm font-mono font-medium text-foreground mt-1">{(run.duration_ms / 1000).toFixed(2)}s</p>
        </div>
      </div>

      {/* Execution Trace */}
      <div className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-foreground mb-4">Execution Trace</h2>
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[11px] top-0 bottom-0 w-px bg-border" />

          <div className="space-y-1">
            {run.stages.map((stage, idx) => {
              const isExpanded = expandedStage === stage.name
              const toolCalls = (stage.output as { tool_calls?: ToolCall[] })?.tool_calls
                ?? (stage.input as { tool_calls?: ToolCall[] })?.tool_calls
                ?? []
              return (
                <div key={`${stage.name}-${idx}`}>
                  <button
                    onClick={() => setExpandedStage(isExpanded ? null : stage.name)}
                    className="flex items-center gap-3 w-full text-left group"
                  >
                    <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center text-[11px] ${
                      stage.status === 'completed' ? 'bg-success text-white' :
                      stage.status === 'failed' ? 'bg-destructive text-white' :
                      'bg-secondary text-muted-foreground'
                    }`}>
                      {stage.status === 'completed' ? <CheckCircle className="w-3.5 h-3.5" /> :
                       stage.status === 'failed' ? <XCircle className="w-3.5 h-3.5" /> :
                       <Clock className="w-3.5 h-3.5" />}
                    </div>
                    <div className="flex-1 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] font-semibold text-foreground capitalize">{stage.name}</span>
                        <span className="text-[10px] text-muted-foreground">{stage.duration_ms}ms</span>
                        {toolCalls.length > 0 && (
                          <span className="text-[10px] text-recovery flex items-center gap-0.5">
                            <Wrench className="w-2.5 h-2.5" />
                            {toolCalls.length} tool{toolCalls.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors">
                      {isExpanded ? 'Collapse' : 'Expand'}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="ml-9 mb-3 p-3 rounded-md bg-secondary/30 border border-border space-y-3">
                      {/* Tool Calls */}
                      {toolCalls.length > 0 && (
                        <div>
                          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Tool Calls</p>
                          <div className="space-y-1">
                            {toolCalls.map((tc, ti) => (
                              <div key={ti} className="flex items-start gap-2 text-[11px] font-mono bg-background/50 rounded p-2">
                                <span className="text-recovery font-semibold shrink-0">{tc.tool_name}</span>
                                <span className="text-muted-foreground">({Math.round(tc.latency_ms)}ms)</span>
                                {tc.error ? (
                                  <span className="text-destructive">{tc.error}</span>
                                ) : (
                                  <span className="text-success">OK</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Input</p>
                        <pre className="text-[11px] text-foreground font-mono bg-background/50 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                          {JSON.stringify(stage.input, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Output</p>
                        <pre className="text-[11px] text-foreground font-mono bg-background/50 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                          {JSON.stringify(stage.output, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
