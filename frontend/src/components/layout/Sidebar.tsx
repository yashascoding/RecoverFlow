import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, CreditCard, AlertTriangle, RotateCcw,
  Bot, FileText, Shield, ChevronLeft, ChevronRight, Activity, Eye, Search, BarChart3
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/sentinel', label: 'Sentinel', icon: Eye },
  { to: '/monitoring', label: 'Monitoring', icon: Activity },
  { to: '/investigations', label: 'Investigations', icon: Search },
  { to: '/payments', label: 'Payments', icon: CreditCard },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/recovery', label: 'Recovery', icon: RotateCcw },
  { to: '/agent-runs', label: 'Agent Runs', icon: Bot },
  { to: '/audit', label: 'Audit', icon: FileText },
  { to: '/policies', label: 'Policies', icon: Shield },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3 },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r border-border bg-card flex flex-col transition-all duration-200',
        collapsed ? 'w-[60px]' : 'w-[220px]'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-border shrink-0">
        <img src="/image.png" alt="RecoverFlow" className="w-7 h-7 rounded-md shrink-0" />
        {!collapsed && (
          <span className="text-[13px] font-semibold text-foreground tracking-tight">
            RecoverFlow
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname.startsWith(item.to)
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                'flex items-center gap-2.5 px-2.5 py-[7px] rounded-md text-[13px] font-medium transition-all duration-150',
                isActive
                  ? 'bg-recovery/10 text-recovery'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
              )}
            >
              <Icon className={cn('w-4 h-4 shrink-0', isActive && 'text-recovery')} />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="border-t border-border p-2 space-y-1 shrink-0">
        <div className={cn(
          'flex items-center gap-2 px-2.5 py-1.5 rounded-md',
          collapsed ? 'justify-center' : ''
        )}>
          <div className="w-2 h-2 rounded-full bg-success shrink-0" />
          {!collapsed && (
            <span className="text-[12px] text-success font-medium">System Healthy</span>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 px-2.5 py-1.5 w-full rounded-md text-[13px] text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
