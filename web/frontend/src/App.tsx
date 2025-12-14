import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { useAuth } from '@/hooks/useAuth'

// Layouts
import { MainLayout } from '@/components/layout/MainLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'

// Pages
import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { IndicesPage } from '@/pages/indices/IndicesPage'
import { IndexBuilderPage } from '@/pages/indices/IndexBuilderPage'
import { IndexDetailPage } from '@/pages/indices/IndexDetailPage'
import { BacktestsPage } from '@/pages/backtests/BacktestsPage'
import { BacktestDetailPage } from '@/pages/backtests/BacktestDetailPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { DataSourcesPage } from '@/pages/settings/DataSourcesPage'
import { DeliveryPage } from '@/pages/settings/DeliveryPage'
import { EmbedsPage } from '@/pages/settings/EmbedsPage'

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected routes */}
        <Route
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/indices" element={<IndicesPage />} />
          <Route path="/indices/new" element={<IndexBuilderPage />} />
          <Route path="/indices/:id" element={<IndexDetailPage />} />
          <Route path="/indices/:id/edit" element={<IndexBuilderPage />} />
          <Route path="/backtests" element={<BacktestsPage />} />
          <Route path="/backtests/:id" element={<BacktestDetailPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/data-sources" element={<DataSourcesPage />} />
          <Route path="/settings/delivery" element={<DeliveryPage />} />
          <Route path="/settings/embeds" element={<EmbedsPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      
      <Toaster />
    </>
  )
}

export default App

