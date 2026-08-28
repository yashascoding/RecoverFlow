import { useLocation, Link } from 'react-router-dom'
import { Search, Bell, ChevronRight } from 'lucide-react'

const routeLabels: Record<string, string> = {
  '/overview': 'Overview',
  '/payments': 'Payments',
  '/incidents': 'Incidents',
  '/recovery': 'Recovery',
  '/agent-runs': 'Agent Runs',
  '/audit': 'Audit Log',
  '/policies': 'Policies',
}

export function Header() {
  const location = useLocation()
  const pathParts = location.pathname.split('/').filter(Boolean)
  const basePath = `/${pathParts[0]}`
  const label = routeLabels[basePath] || 'Dashboard'

  return (
    <header className="h-14 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-30 flex items-center justify-between px-6">
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-1.5 text-sm">
        <Link to="/overview" className="text-muted-foreground hover:text-foreground transition-colors">
          RecoverFlow
        </Link>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-foreground font-medium">{label}</span>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search..."
            className="h-8 w-52 rounded-md border border-border bg-secondary/50 pl-8 pr-3 text-[13px] text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <button className="relative p-1.5 rounded-md hover:bg-secondary transition-colors">
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-recovery" />
        </button>
        <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-[11px] font-medium text-foreground">
          M
        </div>
      </div>
    </header>
  )
}
