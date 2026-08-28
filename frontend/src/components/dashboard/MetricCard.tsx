import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string
  change?: number
  changeLabel?: string
  description?: string
  icon?: React.ReactNode
  className?: string
}

export function MetricCard({ title, value, change, changeLabel, description, icon, className }: MetricCardProps) {
  return (
    <div className={cn('rounded-lg border border-border bg-card p-4', className)}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-[12px] text-muted-foreground font-medium uppercase tracking-wider">{title}</p>
          <p className="text-2xl font-bold text-foreground tracking-tight">{value}</p>
        </div>
        {icon && (
          <div className="p-2 rounded-md bg-secondary/50 text-muted-foreground">
            {icon}
          </div>
        )}
      </div>
      {(change !== undefined || description) && (
        <div className="mt-3 flex items-center gap-2">
          {change !== undefined && (
            <span className={cn(
              'inline-flex items-center gap-0.5 text-[11px] font-medium',
              change > 0 ? 'text-success' : change < 0 ? 'text-destructive-foreground' : 'text-muted-foreground'
            )}>
              {change > 0 ? <TrendingUp className="w-3 h-3" /> : change < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {change > 0 ? '+' : ''}{change.toFixed(1)}%
            </span>
          )}
          {changeLabel && <span className="text-[11px] text-muted-foreground">{changeLabel}</span>}
          {!changeLabel && description && <span className="text-[11px] text-muted-foreground">{description}</span>}
        </div>
      )}
    </div>
  )
}
