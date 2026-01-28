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
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { IndicesPage } from '@/pages/indices/IndicesPage'
import { IndexBuilderPage } from '@/pages/indices/IndexBuilderPage'
import { IndexDetailPage } from '@/pages/indices/IndexDetailPage'
import { RebalancingPage } from '@/pages/indices/RebalancingPage'
import { AnalyticsPage } from '@/pages/indices/AnalyticsPage'
import { BacktestsPage } from '@/pages/backtests/BacktestsPage'
import { BacktestDetailPage } from '@/pages/backtests/BacktestDetailPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { PricingPage } from '@/pages/settings/PricingPage'
import { DataSourcesPage } from '@/pages/data-sources/DataSourcesPage'
import { DeliveryPage } from '@/pages/settings/DeliveryPage'
import { EmbedsPage } from '@/pages/settings/EmbedsPage'
import { TeamsPage } from '@/pages/teams/TeamsPage'
import { ContactPage } from '@/pages/ContactPage'

// Admin
import { AdminRoute } from '@/components/auth/AdminRoute'
import { AdminLayout } from '@/components/layout/AdminLayout'
import { AdminDashboardPage } from '@/pages/admin/DashboardPage'
import { UsersPage } from '@/pages/admin/UsersPage'

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = window.location

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    // Get the current path to redirect back after login
    const currentPath = location.pathname + location.search
    const redirectUrl = currentPath !== '/' ? `?redirect=${encodeURIComponent(currentPath)}&session_expired=true` : ''
    return <Navigate to={`/login${redirectUrl}`} replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/contact" element={<ContactPage />} />

        {/* Auth routes */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Password reset routes (standalone, no layout) */}
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />

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
          <Route path="/indices/:id/rebalancing" element={<RebalancingPage />} />
          <Route path="/indices/:id/analytics" element={<AnalyticsPage />} />
          <Route path="/backtests" element={<BacktestsPage />} />
          <Route path="/backtests/:id" element={<BacktestDetailPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/data-sources" element={<DataSourcesPage />} />
          <Route path="/delivery" element={<DeliveryPage />} />
          <Route path="/embeds" element={<EmbedsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          {/* Legacy redirects */}
          <Route path="/settings/data-sources" element={<DataSourcesPage />} />
          <Route path="/settings/delivery" element={<DeliveryPage />} />
          <Route path="/settings/embeds" element={<EmbedsPage />} />
        </Route>

        {/* Admin routes */}
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminLayout />
            </AdminRoute>
          }
        >
          <Route path="dashboard" element={<AdminDashboardPage />} />
          <Route path="users" element={<UsersPage />} />
          {/* Redirect /admin to dashboard */}
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <Toaster />
    </>
  )
}

export default App
