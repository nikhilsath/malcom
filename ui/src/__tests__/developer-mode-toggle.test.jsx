import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from '../App'

describe('Developer mode toggle', () => {
  it('renders with stable ID and persists in sessionStorage', async () => {
    const user = userEvent.setup()
    window.sessionStorage.clear()

    render(<App />)

    const toggle = screen.getByLabelText('Toggle developer mode')
    expect(toggle).toHaveAttribute('id', 'topbar-developer-mode-toggle')
    expect(window.sessionStorage.getItem('developerMode')).toBe('false')

    await user.click(toggle)

    expect(window.sessionStorage.getItem('developerMode')).toBe('true')
  })
})
