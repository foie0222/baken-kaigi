import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../test/utils'
import { SettingsPage } from './SettingsPage'
import { useAuthStore } from '../stores/authStore'

vi.mock('../stores/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../stores/cookieConsentStore', () => ({
  useCookieConsentStore: vi.fn(() => vi.fn()),
}))

describe('SettingsPage', () => {
  it('認証済みの場合、ヘルプがボタンとして表示される', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: true,
      signOut: vi.fn(),
    } as ReturnType<typeof useAuthStore>)

    render(<SettingsPage />)
    const helpButton = screen.getByRole('button', { name: /ヘルプ/ })
    expect(helpButton).toBeInTheDocument()
  })

  it('未認証の場合もヘルプがボタンとして表示される', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: false,
      signOut: vi.fn(),
    } as ReturnType<typeof useAuthStore>)

    render(<SettingsPage />)
    const helpButton = screen.getByRole('button', { name: /ヘルプ/ })
    expect(helpButton).toBeInTheDocument()
  })

  it('認証済みの場合、アカウントセクションが表示される', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: true,
      signOut: vi.fn(),
    } as ReturnType<typeof useAuthStore>)

    render(<SettingsPage />)
    expect(screen.getByText('アカウント')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /プロフィール/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /パスワード変更/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /IPAT設定/ })).toBeInTheDocument()
  })

  it('未認証の場合、ログインボタンが表示される', () => {
    vi.mocked(useAuthStore).mockReturnValue({
      isAuthenticated: false,
      signOut: vi.fn(),
    } as ReturnType<typeof useAuthStore>)

    render(<SettingsPage />)
    expect(screen.getByText(/ログイン/)).toBeInTheDocument()
  })
})
