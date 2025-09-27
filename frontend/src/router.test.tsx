import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '@/test/utils'

describe('App routing', () => {
  it('redirects root to dashboard', async () => {
    const { router } = renderWithRouter(['/'])

    await screen.findByText('Filing intelligence at a glance')

    expect(router.state.location.pathname).toBe('/dashboard')
  })

  it('navigates between primary routes', async () => {
    const user = userEvent.setup()

    renderWithRouter(['/dashboard'])

    await screen.findByText('Filing intelligence at a glance')

    await user.click(await screen.findByRole('link', { name: 'Learn' }))

    await screen.findByText('Build your filing fluency')

    await user.click(await screen.findByRole('link', { name: 'Saved' }))

    await screen.findByText('Keep your research within reach')
  })

  it('renders filing detail route with provided id', async () => {
    const filingId = 'demo-10q'

    renderWithRouter([`/filing/${filingId}`])

    await screen.findByText(filingId.toUpperCase())
    await screen.findByText('Filing Detail')
  })
})
