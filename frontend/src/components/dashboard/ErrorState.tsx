import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({ title = 'Something went wrong', message, onRetry, className }: ErrorStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      <div className="mb-3 p-2 rounded-full bg-destructive/10">
        <AlertTriangle className="w-5 h-5 text-red-400" />
      </div>
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      <p className="text-[13px] text-muted-foreground mt-1 max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary text-[13px] font-medium text-foreground hover:bg-secondary/80 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      )}
    </div>
  )
}
