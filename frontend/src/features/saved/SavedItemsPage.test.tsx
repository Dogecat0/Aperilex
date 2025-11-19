import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import type * as ReactRouterDomModule from 'react-router-dom'
import { apiClient } from '@/lib/apiClient'
import { renderWithProviders } from '@/test/utils'
import { SavedItemsPage } from './SavedItemsPage'

const mockNavigate = vi.fn()
const getSpy = vi.spyOn(apiClient, 'get')
const deleteSpy = vi.spyOn(apiClient, 'delete')

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual<ReactRouterDomModule>('react-router-dom')
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    }
})

// Mock the useSavedAnalyses hook
const mockRemove = vi.fn()
const mockSavedAnalyses = [
    {
        analysisId: '123',
        companyName: 'Test Company',
        ticker: 'TST',
        filingType: '10-K',
        filingDate: '2023-01-01T00:00:00Z',
        savedAt: '2023-01-02T00:00:00Z',
    },
    {
        analysisId: '456',
        companyName: 'Another Company',
        ticker: 'ABC',
        filingType: '10-Q',
        filingDate: '2023-02-01T00:00:00Z',
        savedAt: '2023-02-02T00:00:00Z',
    },
]

vi.mock('@/lib/hooks', async () => {
    const actual = await vi.importActual('@/lib/hooks')
    return {
        ...actual,
        useSavedAnalyses: () => ({
            savedAnalyses: mockSavedAnalyses,
            remove: mockRemove,
        }),
    }
})

beforeEach(() => {
    getSpy.mockReset()
    deleteSpy.mockReset()
    mockNavigate.mockReset()
    mockRemove.mockReset()
})

afterEach(() => {
    vi.clearAllMocks()
})

describe('SavedItemsPage', () => {
    it('renders saved analyses', async () => {
        renderWithProviders(<SavedItemsPage />)

        expect(screen.getByText('Test Company')).toBeInTheDocument()
        expect(screen.getByText('Another Company')).toBeInTheDocument()
        expect(screen.getByText('TST')).toBeInTheDocument()
        expect(screen.getByText('ABC')).toBeInTheDocument()
    })

    it('navigates to analysis on open', async () => {
        getSpy.mockResolvedValue({}) // Mock successful existence check

        renderWithProviders(<SavedItemsPage />)

        const openButtons = screen.getAllByText('Open Analysis')
        fireEvent.click(openButtons[0])

        await waitFor(() => {
            expect(getSpy).toHaveBeenCalledWith('/analyses/123', expect.anything())
            expect(mockNavigate).toHaveBeenCalledWith('/filing/123')
        })
    })

    it('calls remove when remove button is clicked', async () => {
        renderWithProviders(<SavedItemsPage />)

        const removeButtons = screen.getAllByText('Remove')
        fireEvent.click(removeButtons[0])

        expect(mockRemove).toHaveBeenCalledWith('123')
    })
})
