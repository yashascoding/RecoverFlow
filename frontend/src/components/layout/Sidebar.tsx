import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, CreditCard, AlertTriangle, RotateCcw,
  Bot, FileText, Shield, ChevronLeft, ChevronRight, Activity
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/payments', label: 'Payments', icon: CreditCard },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/recovery', label: 'Recovery', icon: RotateCcw },
  { to: '/agent-runs', label: 'Agent Runs', icon: Bot },
  { to: '/audit', label: 'Audit', icon: FileText },
  { to: '/policies', label: 'Policies', icon: Shield },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r border-border bg-[#0c0c0e] flex flex-col transition-all duration-200',
        collapsed ? 'w-[60px]' : 'w-[220px]'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-border shrink-0">
        <div className="w-7 h-7 rounded-md bg-recovery flex items-center justify-center text-white text-xs font-bold shrink-0">
          RF
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-foreground tracking-tight">
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
                'flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] font-medium transition-colors',
                isActive
                  ? 'bg-secondary text-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="border-t border-border p-2 space-y-1 shrink-0">
        <div className="flex items-center gap-2 px-2.5 py-1.5">
          <Activity className="w-3.5 h-3.5 text-success" />
          {!collapsed && (
            <span className="text-[11px] text-muted-foreground">System Healthy</span>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 px-2.5 py-1.5 w-full rounded-md text-[13px] text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
