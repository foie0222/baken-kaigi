import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import { LoginPage } from './LoginPage'
import { useAuthStore } from '../../stores/authStore'

describe('LoginPage', () => {
  const originalState = useAuthStore.getState()

  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, error: null })
  })

  afterEach(() => {
    useAuthStore.setState(originalState)
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
    const emailInput = screen.getByLabelText('メールアドレス')
    await user.type(emailInput, 'test@example.com')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('パスワードのみ入力でメールアドレスが空の場合はログインボタンが無効', async () => {
    const { user } = render(<LoginPage />)
    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('不正なメールアドレスの場合はログインボタンが無効', async () => {
    const { user } = render(<LoginPage />)
    const emailInput = screen.getByLabelText('メールアドレス')
    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(emailInput, 'not-an-email')
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).toBeDisabled()
  })

  it('有効なメールアドレスとパスワードでログインボタンが有効', async () => {
    const { user } = render(<LoginPage />)
    const emailInput = screen.getByLabelText('メールアドレス')
    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    const button = screen.getByRole('button', { name: 'ログイン' })
    expect(button).not.toBeDisabled()
  })

  it('有効な入力でsignInが呼ばれる', async () => {
    const mockSignIn = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({ signIn: mockSignIn } as never)

    const { user } = render(<LoginPage />)
    const emailInput = screen.getByLabelText('メールアドレス')
    const passwordInput = screen.getByLabelText('パスワード')
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
