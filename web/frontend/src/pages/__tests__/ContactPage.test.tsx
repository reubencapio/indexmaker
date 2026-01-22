import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ContactPage } from '../ContactPage'
import { MemoryRouter } from 'react-router-dom'
import { supportApi } from '@/lib/api'
import * as useAuthHook from '@/hooks/useAuth'

// Mock dependencies
vi.mock('@/lib/api', () => ({
    supportApi: {
        contact: vi.fn(),
    },
}))

vi.mock('@/hooks/useAuth', () => ({
    useAuth: vi.fn(),
}))

// Mock scrollIntoView
window.scrollTo = vi.fn() as any

describe('ContactPage', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        // Default auth state: logged out
        vi.spyOn(useAuthHook, 'useAuth').mockReturnValue({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            login: vi.fn(),
            logout: vi.fn(),
            register: vi.fn(),
            clearError: vi.fn(),
        })
    })

    it('renders contact form correctly', () => {
        render(
            <MemoryRouter>
                <ContactPage />
            </MemoryRouter>
        )

        expect(screen.getByRole('heading', { name: /Contact Us/i })).toBeInTheDocument()
        expect(screen.getByLabelText(/Your Name/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/Subject/i)).toBeInTheDocument()
        expect(screen.getByLabelText(/Message/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Send Message/i })).toBeInTheDocument()
    })

    it('pre-fills user data when logged in', () => {
        vi.spyOn(useAuthHook, 'useAuth').mockReturnValue({
            user: {
                id: '1',
                email: 'test@example.com',
                full_name: 'Test User',
                is_active: true,
                is_verified: true,
                role: 'user',
                tier: 'free',
            },
            isAuthenticated: true,
            isLoading: false,
            error: null,
            login: vi.fn(),
            logout: vi.fn(),
            register: vi.fn(),
            clearError: vi.fn(),
        })

        render(
            <MemoryRouter>
                <ContactPage />
            </MemoryRouter>
        )

        expect(screen.getByDisplayValue('Test User')).toBeInTheDocument()
        expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
    })

    it('submits form successfully and shows success state', async () => {
        (supportApi.contact as any).mockResolvedValue({ status: 'success' })

        render(
            <MemoryRouter>
                <ContactPage />
            </MemoryRouter>
        )

        // Fill form
        fireEvent.change(screen.getByLabelText(/Your Name/i), { target: { value: 'John Doe' } })
        fireEvent.change(screen.getByLabelText(/Email Address/i), { target: { value: 'john@example.com' } })
        fireEvent.change(screen.getByLabelText(/Message/i), { target: { value: 'Hello support' } })

        // Submit
        fireEvent.click(screen.getByRole('button', { name: /Send Message/i }))

        // Check loading state
        expect(screen.getByRole('button', { name: /Sending.../i })).toBeInTheDocument()

        // Wait for success
        await waitFor(() => {
            expect(screen.getByText(/Message Sent!/i)).toBeInTheDocument()
        })

        expect(supportApi.contact).toHaveBeenCalledWith(expect.objectContaining({
            name: 'John Doe',
            email: 'john@example.com',
            message: 'Hello support',
        }))
    })
})
