import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="pl-[220px]">
        <Header />
        <main className="min-h-[calc(100vh-56px)]">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
