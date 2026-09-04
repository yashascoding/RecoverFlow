import { useState } from 'react'
import {
  TrendingUp, TrendingDown, Minus, DollarSign, AlertTriangle, RotateCcw,
  Mail, Bot, Shield, BarChart3, Play, Users, Zap, CheckCircle2, XCircle,
  Clock, ArrowUpRight
} from 'lucide-react'
import { PageContainer } from '@/components/layout/PageContainer'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MetricCardSkeleton } from '@/components/dashboard/LoadingState'
import { StatusBadge } from '@/components/dashboard/StatusBadge'
import { useApi } from '@/hooks/useApi'
import { getEvaluationDashboard } from '@/api/evaluation'
import { formatCurrency } from '@/lib/utils'
import type {
  RecoveryMetrics, EmailMetrics, AgentMetrics, PolicyMetrics,
  CostMetrics, AssignmentGroupMetrics, LiftResult
} from '@/types'

function SectionHeader({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="p-2 rounded-md bg-secondary text-muted-foreground">
        {icon}
      </div>
      <div>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <p className="text-[12px] text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

function MetricRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
      <span className="text-[13px] text-muted-foreground">{label}</span>
      <div className="text-right">
        <span className="text-[13px] font-medium text-foreground">{value}</span>
        {sub && <span className="text-[11px] text-muted-foreground ml-2">{sub}</span>}
      </div>
    </div>
  )
}

function GroupComparisonCard({
  control,
  ai,
  lift,
}: {
  control: AssignmentGroupMetrics
  ai: AssignmentGroupMetrics
  lift: LiftResult
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <SectionHeader
        icon={<BarChart3 className="w-4 h-4" />}
        title="Control vs AI Group"
        description="A/B test performance comparison"
      />

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center p-3 rounded-md bg-secondary/50 border border-border">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">Control (10%)</p>
          <p className="text-[22px] font-bold text-foreground">{control.recovery_rate}%</p>
          <p className="text-[11px] text-muted-foreground mt-1">{control.payment_count} payments</p>
        </div>
        <div className="text-center p-3 rounded-md bg-recovery/5 border border-recovery/20">
          <p className="text-[11px] text-recovery uppercase tracking-wider mb-1">AI Group (90%)</p>
          <p className="text-[22px] font-bold text-recovery">{ai.recovery_rate}%</p>
          <p className="text-[11px] text-muted-foreground mt-1">{ai.payment_count} payments</p>
        </div>
        <div className="text-center p-3 rounded-md bg-secondary/50 border border-border">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1">Lift</p>
          <p className={`text-[22px] font-bold ${lift.lift_absolute > 0 ? 'text-success' : lift.lift_absolute < 0 ? 'text-red-400' : 'text-foreground'}`}>
            {lift.lift_absolute > 0 ? '+' : ''}{lift.lift_absolute}%
          </p>
          <p className="text-[11px] text-muted-foreground mt-1">
            {lift.is_statistically_significant ? 'Significant' : 'Need more data'}
          </p>
        </div>
      </div>

      <div className="space-y-0">
        <MetricRow
          label="Control Recovered Revenue"
          value={formatCurrency(control.recovered_revenue)}
        />
        <MetricRow
          label="AI Recovered Revenue"
          value={formatCurrency(ai.recovered_revenue)}
        />
        <MetricRow
          label="Revenue Lift"
          value={formatCurrency(ai.recovered_revenue - control.recovered_revenue)}
          sub={ai.recovered_revenue > control.recovered_revenue ? 'AI outperforms' : 'Control outperforms'}
        />
      </div>
    </div>
  )
}

function PolicyComplianceCard({ metrics }: { metrics: PolicyMetrics }) {
  const complianceColor = metrics.compliance_rate >= 95 ? 'text-success' : metrics.compliance_rate >= 80 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <SectionHeader
        icon={<Shield className="w-4 h-4" />}
        title="Policy Compliance"
        description="Policy engine decisions and compliance"
      />
      <div className="space-y-0">
        <MetricRow label="Total Decisions" value={String(metrics.total_decisions)} />
        <MetricRow label="Allowed" value={String(metrics.allowed)} sub={`${metrics.total_decisions ? ((metrics.allowed / metrics.total_decisions) * 100).toFixed(1) : 0}%`} />
        <MetricRow label="Blocked" value={String(metrics.blocked)} sub={`${metrics.total_decisions ? ((metrics.blocked / metrics.total_decisions) * 100).toFixed(1) : 0}%`} />
        <MetricRow label="Human Review" value={String(metrics.human_review)} />
        <MetricRow label="Violations" value={String(metrics.violations)} />
        <div className="flex items-center justify-between py-2">
          <span className="text-[13px] text-muted-foreground">Compliance Rate</span>
          <span className={`text-[15px] font-bold ${complianceColor}`}>{metrics.compliance_rate}%</span>
        </div>
      </div>
    </div>
  )
}

function CostBreakdownCard({ metrics }: { metrics: CostMetrics }) {
  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <SectionHeader
        icon={<DollarSign className="w-4 h-4" />}
        title="Cost Analysis"
        description="AI and email costs vs recovered revenue"
      />
      <div className="space-y-0">
        <MetricRow label="AI Cost" value={`$${metrics.ai_cost_usd.toFixed(4)}`} />
        <MetricRow label="Email Cost" value={`$${metrics.email_cost_usd.toFixed(4)}`} />
        <MetricRow label="Total Cost" value={`$${metrics.total_cost_usd.toFixed(4)}`} />
        <MetricRow label="Recovered Revenue" value={`$${metrics.recovered_revenue_usd.toFixed(2)}`} />
        <MetricRow label="Net Recovered Revenue" value={`$${metrics.net_recovered_revenue_usd.toFixed(2)}`} />
        <div className="flex items-center justify-between py-2">
          <span className="text-[13px] text-muted-foreground">ROI</span>
          <span className={`text-[15px] font-bold ${metrics.roi > 0 ? 'text-success' : 'text-red-400'}`}>
            {metrics.roi > 0 ? '+' : ''}{metrics.roi}%
          </span>
        </div>
      </div>
    </div>
  )
}

export function EvaluationPage() {
  const [timeWindow, setTimeWindow] = useState(168)
  const { data, loading, error, refetch } = useApi(() => getEvaluationDashboard(timeWindow), [timeWindow])

  const timeWindowOptions = [
    { value: 24, label: '24h' },
    { value: 72, label: '3d' },
    { value: 168, label: '7d' },
    { value: 720, label: '30d' },
  ]

  return (
    <PageContainer
      title="Evaluation Dashboard"
      description="Recovery performance metrics, A/B test results, and cost analysis"
      actions={
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border bg-card overflow-hidden">
            {timeWindowOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTimeWindow(opt.value)}
                className={`px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  timeWindow === opt.value
                    ? 'bg-recovery text-white'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 rounded-md border border-border bg-card text-[12px] font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
          >
            Refresh
          </button>
        </div>
      }
    >
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
          <p className="text-[13px] text-red-400">{error}</p>
        </div>
      )}

      {/* Recovery Metrics */}
      <SectionHeader
        icon={<RotateCcw className="w-4 h-4" />}
        title="Recovery Metrics"
        description="Payment recovery performance"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : data ? (
          <>
            <MetricCard
              title="Recovery Rate"
              value={`${data.recovery.recovery_rate}%`}
              description={`${data.recovery.total_recovered} of ${data.recovery.total_failed} failed`}
              icon={<TrendingUp className="w-4 h-4" />}
            />
            <MetricCard
              title="Recovered Revenue"
              value={formatCurrency(data.recovery.recovered_revenue)}
              description="Successfully recovered"
              icon={<DollarSign className="w-4 h-4" />}
            />
            <MetricCard
              title="Revenue At Risk"
              value={formatCurrency(data.recovery.revenue_at_risk)}
              description="Pending recovery"
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Total Payments"
              value={String(data.recovery.total_payments)}
              description={`${data.recovery.total_failed} failed`}
              icon={<BarChart3 className="w-4 h-4" />}
            />
          </>
        ) : null}
      </div>

      {/* Email Metrics */}
      <SectionHeader
        icon={<Mail className="w-4 h-4" />}
        title="Email Metrics"
        description="Recovery email delivery and engagement"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : data ? (
          <>
            <MetricCard
              title="Sent"
              value={String(data.email.total_sent)}
              icon={<Mail className="w-4 h-4" />}
            />
            <MetricCard
              title="Delivered"
              value={String(data.email.total_delivered)}
              description={`${data.email.delivery_rate}%`}
              icon={<CheckCircle2 className="w-4 h-4" />}
            />
            <MetricCard
              title="Opened"
              value={String(data.email.total_opened)}
              description={`${data.email.open_rate}%`}
              icon={<Mail className="w-4 h-4" />}
            />
            <MetricCard
              title="Clicked"
              value={String(data.email.total_clicked)}
              description={`${data.email.click_rate}%`}
              icon={<ArrowUpRight className="w-4 h-4" />}
            />
            <MetricCard
              title="Converted"
              value={String(data.email.total_converted)}
              description={`${data.email.conversion_rate}%`}
              icon={<CheckCircle2 className="w-4 h-4" />}
            />
          </>
        ) : null}
      </div>

      {/* Agent Metrics */}
      <SectionHeader
        icon={<Bot className="w-4 h-4" />}
        title="Agent Metrics"
        description="AI agent execution performance"
      />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <MetricCardSkeleton key={i} />)
        ) : data ? (
          <>
            <MetricCard
              title="Successful Runs"
              value={String(data.agent.successful_runs)}
              description={`${data.agent.success_rate}% success rate`}
              icon={<CheckCircle2 className="w-4 h-4" />}
            />
            <MetricCard
              title="Failed Runs"
              value={String(data.agent.failed_runs)}
              icon={<XCircle className="w-4 h-4" />}
            />
            <MetricCard
              title="Tool Errors"
              value={String(data.agent.tool_errors)}
              icon={<AlertTriangle className="w-4 h-4" />}
            />
            <MetricCard
              title="Avg Latency"
              value={`${data.agent.avg_latency_ms.toFixed(0)}ms`}
              description={`P95: ${data.agent.p95_latency_ms.toFixed(0)}ms`}
              icon={<Clock className="w-4 h-4" />}
            />
          </>
        ) : null}
      </div>

      {/* Policy + Cost + Control Group */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {loading ? (
          <>
            <div className="rounded-lg border border-border bg-card p-5 h-[300px] animate-pulse" />
            <div className="rounded-lg border border-border bg-card p-5 h-[300px] animate-pulse" />
          </>
        ) : data ? (
          <>
            <PolicyComplianceCard metrics={data.policy} />
            <CostBreakdownCard metrics={data.cost} />
          </>
        ) : null}
      </div>

      {/* Control Group Comparison */}
      {loading ? (
        <div className="rounded-lg border border-border bg-card p-5 h-[300px] animate-pulse" />
      ) : data ? (
        <GroupComparisonCard
          control={data.control_group}
          ai={data.ai_group}
          lift={data.lift}
        />
      ) : null}

      {/* Summary Bar */}
      {data && (
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-recovery" />
                <span className="text-[12px] text-muted-foreground">
                  Recovery: <span className="text-foreground font-medium">{data.recovery.recovery_rate}%</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success" />
                <span className="text-[12px] text-muted-foreground">
                  Net Revenue: <span className="text-foreground font-medium">${data.cost.net_recovered_revenue_usd.toFixed(2)}</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-400" />
                <span className="text-[12px] text-muted-foreground">
                  Policy Compliance: <span className="text-foreground font-medium">{data.policy.compliance_rate}%</span>
                </span>
              </div>
              {data.lift.lift_absolute !== 0 && (
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${data.lift.lift_absolute > 0 ? 'bg-success' : 'bg-red-400'}`} />
                  <span className="text-[12px] text-muted-foreground">
                    AI Lift: <span className={`font-medium ${data.lift.lift_absolute > 0 ? 'text-success' : 'text-red-400'}`}>
                      {data.lift.lift_absolute > 0 ? '+' : ''}{data.lift.lift_absolute}%
                    </span>
                  </span>
                </div>
              )}
            </div>
            <span className="text-[11px] text-muted-foreground">
              Window: {data.time_window_hours}h · Generated: {new Date(data.generated_at).toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </PageContainer>
  )
}
