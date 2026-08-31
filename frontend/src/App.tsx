import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { AuthProvider } from '@/hooks/useAuth'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Layout } from '@/components/layout/Layout'
import { LandingPage } from '@/pages/landing/LandingPage'
import { AuthPage } from '@/pages/auth/AuthPage'
import { OverviewPage } from '@/pages/overview/OverviewPage'
import { PaymentsPage } from '@/pages/payments/PaymentsPage'
import { PaymentDetailPage } from '@/pages/payments/PaymentDetailPage'
import { IncidentsPage } from '@/pages/incidents/IncidentsPage'
import { IncidentDetailPage } from '@/pages/incidents/IncidentDetailPage'
import { RecoveryPage } from '@/pages/recovery/RecoveryPage'
import { AgentRunsPage } from '@/pages/agent-runs/AgentRunsPage'
import { AgentRunDetailPage } from '@/pages/agent-runs/AgentRunDetailPage'
import { AuditPage } from '@/pages/audit/AuditPage'
import { PoliciesPage } from '@/pages/policies/PoliciesPage'
import { DecisionReplayPage } from '@/pages/replay/DecisionReplayPage'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          theme="dark"
          toastOptions={{
            style: {
              background: '#27272a',
              border: '1px solid #3f3f46',
              color: '#fafafa',
              fontSize: '13px',
            },
          }}
        />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="/register" element={<AuthPage />} />
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/payments" element={<PaymentsPage />} />
            <Route path="/payments/:id" element={<PaymentDetailPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/incidents/:id" element={<IncidentDetailPage />} />
            <Route path="/recovery" element={<RecoveryPage />} />
            <Route path="/agent-runs" element={<AgentRunsPage />} />
            <Route path="/agent-runs/:id" element={<AgentRunDetailPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/policies" element={<PoliciesPage />} />
            <Route path="/replay/:paymentId" element={<DecisionReplayPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
