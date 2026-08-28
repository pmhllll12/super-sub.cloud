import { render, screen } from '@testing-library/react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

describe('GoogleSignInButton', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('NEXT_PUBLIC_GOOGLE_CLIENT_ID 가 없으면 아무것도 그리지 않는다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', '')
    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('NEXT_PUBLIC_GOOGLE_CLIENT_ID 가 있으면 버튼을 그린다(로드 전에는 비활성)', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    render(<GoogleSignInButton onError={() => {}} />)
    const button = screen.getByRole('button', { name: 'Google로 계속하기' })
    expect(button).toBeInTheDocument()
    expect(button).toBeDisabled()
  })
})
