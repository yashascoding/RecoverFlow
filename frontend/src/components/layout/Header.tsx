import { useLocation, Link, useNavigate } from 'react-router-dom'
import { ChevronRight, LogOut } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

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
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const pathParts = location.pathname.split('/').filter(Boolean)
  const basePath = `/${pathParts[0]}`
  const label = routeLabels[basePath] || 'Dashboard'

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const initial = user?.name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'

  return (
    <header className="h-14 border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center gap-1.5 text-sm">
        <Link to="/overview" className="text-muted-foreground hover:text-foreground transition-colors">
          RecoverFlow
        </Link>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        <span className="text-foreground font-medium">{label}</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-[11px] font-medium text-foreground">
          {initial}
        </div>
        <button
          onClick={handleLogout}
          className="p-1.5 rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
