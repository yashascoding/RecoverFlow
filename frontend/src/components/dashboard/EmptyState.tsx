import { cn } from '@/lib/utils'

interface EmptyStateProps {
  title: string
  description: string
  icon?: React.ReactNode
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ title, description, icon, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-10 text-center', className)}>
      {icon && <div className="mb-3 text-muted-foreground/50">{icon}</div>}
      <h3 className="text-[13px] font-medium text-foreground">{title}</h3>
      <p className="text-[12px] text-muted-foreground mt-1 max-w-sm leading-relaxed">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
