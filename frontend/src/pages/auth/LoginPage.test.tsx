import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '../../stores/authStore'

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, error: null })
  })

  it('ログインフォームが表示される', () => {
    render(<LoginPage />)
    expect(screen.getByText('ログイン', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'ログイン' })).toBeInTheDocument()
  })

  it('メールアドレスとパスワードが空の場合はログインボタンが無効', () => {
    render(<LoginPage />)
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('メールアドレスのみ入力でパスワードが空の場合はログインボタンが無効', async () => {
    const { user } = render(<LoginPage />)
    const emailInput = screen.getByPlaceholderText('example@email.com')
    await user.type(emailInput, 'test@example.com')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('パスワードのみ入力でメールアドレスが空の場合はログインボタンが無効', async () => {
    const { user } = render(<LoginPage />)
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('不正なメールアドレスの場合はログインボタンが無効', async () => {
    const { user } = render(<LoginPage />)
    const emailInput = screen.getByPlaceholderText('example@email.com')
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
    await user.type(emailInput, 'not-an-email')
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('有効なメールアドレスとパスワードでログインボタンが有効', async () => {
    const { user } = render(<LoginPage />)
    const emailInput = screen.getByPlaceholderText('example@email.com')
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).not.toBeDisabled()
  })

  it('有効な入力でsignInが呼ばれる', async () => {
    const mockSignIn = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({ signIn: mockSignIn } as never)

    const { user } = render(<LoginPage />)
    const emailInput = screen.getByPlaceholderText('example@email.com')
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(screen.getByRole('button', { name: 'ログイン' }))
    expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'password123')
  })

  it('ストアからのエラーメッセージが表示される', () => {
    useAuthStore.setState({ error: 'メールアドレスまたはパスワードが正しくありません' })
    render(<LoginPage />)
    expect(screen.getByText('メールアドレスまたはパスワードが正しくありません')).toBeInTheDocument()
  })

  it('パスワードを忘れた方リンクが表示される', () => {
    render(<LoginPage />)
    expect(screen.getByRole('link', { name: 'パスワードを忘れた方' })).toBeInTheDocument()
  })

  it('新規登録リンクが表示される', () => {
    render(<LoginPage />)
    expect(screen.getByRole('link', { name: '新規登録' })).toBeInTheDocument()
  })
})
