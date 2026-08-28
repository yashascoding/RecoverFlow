import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="pl-[220px]">
        <Header />
        <main className="min-h-[calc(100vh-56px)]">
          {children}
        </main>
      </div>
    </div>
  )
}
