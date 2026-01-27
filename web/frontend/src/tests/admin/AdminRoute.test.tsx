
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AdminRoute } from '@/components/auth/AdminRoute'
import * as useAuthHook from '@/hooks/useAuth'

// Mock useAuth
const useAuthSpy = vi.spyOn(useAuthHook, 'useAuth')

describe('AdminRoute', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('shows loading spinner when loading', () => {
        useAuthSpy.mockReturnValue({
            user: null,
            isAuthenticated: false,
            isLoading: true,
            error: null,
            login: vi.fn(),
            register: vi.fn(),
            logout: vi.fn(),
            clearError: vi.fn(),
        })

        const { container } = render(
            <MemoryRouter>
                <AdminRoute>
                    <div>Admin Content</div>
                </AdminRoute>
            </MemoryRouter>
        )

        // Basic check for spinner div (class-based check is brittle, but valid for now)
        expect(container.getElementsByClassName('animate-spin').length).toBe(1)
    })

    it('redirects to login if not authenticated', () => {
        useAuthSpy.mockReturnValue({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            login: vi.fn(),
            register: vi.fn(),
            logout: vi.fn(),
            clearError: vi.fn(),
        })

        render(
            <MemoryRouter initialEntries={['/admin']}>
                <Routes>
                    <Route path="/admin" element={
                        <AdminRoute>
                            <div>Admin Content</div>
                        </AdminRoute>
                    } />
                    <Route path="/login" element={<div>Login Page</div>} />
                </Routes>
            </MemoryRouter>
        )

        expect(screen.getByText('Login Page')).toBeInTheDocument()
    })

    it('redirects to dashboard if authenticated but not admin', () => {
        useAuthSpy.mockReturnValue({
            user: { id: '1', role: 'user', email: 'test@example.com' } as any,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            login: vi.fn(),
            register: vi.fn(),
            logout: vi.fn(),
            clearError: vi.fn(),
        })

        render(
            <MemoryRouter initialEntries={['/admin']}>
                <Routes>
                    <Route path="/admin" element={
                        <AdminRoute>
                            <div>Admin Content</div>
                        </AdminRoute>
                    } />
                    <Route path="/dashboard" element={<div>User Dashboard</div>} />
                </Routes>
            </MemoryRouter>
        )

        expect(screen.getByText('User Dashboard')).toBeInTheDocument()
    })

    it('renders children if authenticated and admin', () => {
        useAuthSpy.mockReturnValue({
            user: { id: '1', role: 'admin', email: 'admin@example.com' } as any,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            login: vi.fn(),
            register: vi.fn(),
            logout: vi.fn(),
            clearError: vi.fn(),
        })

        render(
            <MemoryRouter initialEntries={['/admin']}>
                <AdminRoute>
                    <div>Admin Content</div>
                </AdminRoute>
            </MemoryRouter>
        )

        expect(screen.getByText('Admin Content')).toBeInTheDocument()
    })
})
