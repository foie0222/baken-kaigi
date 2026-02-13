import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { useAuthStore } from '../../stores/authStore'

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, error: null })
  })

  it('パスワードリセットフォームが表示される', () => {
    render(<ForgotPasswordPage />)
    expect(screen.getByText('パスワードリセット')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'リセットコードを送信' })).toBeInTheDocument()
  })

  it('メールアドレスが空の場合は送信ボタンが無効', () => {
    render(<ForgotPasswordPage />)
    const button = screen.getByRole('button', { name: 'リセットコードを送信' })
    expect(button).toBeDisabled()
  })

  it('不正なメールアドレスの場合はバリデーションエラーが表示される', async () => {
    const { user } = render(<ForgotPasswordPage />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'not-an-email')
    const button = screen.getByRole('button', { name: 'リセットコードを送信' })
    await user.click(button)
    expect(screen.getByText('有効なメールアドレスを入力してください')).toBeInTheDocument()
  })

  it('有効なメールアドレスの場合は送信ボタンが有効', async () => {
    const { user } = render(<ForgotPasswordPage />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'test@example.com')
    const button = screen.getByRole('button', { name: 'リセットコードを送信' })
    expect(button).not.toBeDisabled()
  })

  it('有効なメールアドレスでforgotPasswordが呼ばれる', async () => {
    const mockForgotPassword = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({ forgotPassword: mockForgotPassword } as never)

    const { user } = render(<ForgotPasswordPage />)
    const input = screen.getByRole('textbox')
    await user.type(input, 'test@example.com')
    await user.click(screen.getByRole('button', { name: 'リセットコードを送信' }))
    expect(mockForgotPassword).toHaveBeenCalledWith('test@example.com')
  })

  it('ストアからのエラーメッセージが表示される', () => {
    useAuthStore.setState({ error: 'ユーザーが見つかりません' })
    render(<ForgotPasswordPage />)
    expect(screen.getByText('ユーザーが見つかりません')).toBeInTheDocument()
  })

  it('ログインに戻るリンクが表示される', () => {
    render(<ForgotPasswordPage />)
    expect(screen.getByRole('link', { name: 'ログインに戻る' })).toBeInTheDocument()
  })
})
