import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import { SignUpPage } from './SignUpPage'
import { useAuthStore } from '../../stores/authStore'

describe('SignUpPage', () => {
  const originalState = useAuthStore.getState()

  beforeEach(() => {
    useAuthStore.setState({ isLoading: false, error: null })
  })

  afterEach(() => {
    useAuthStore.setState(originalState)
  })

  it('新規登録フォームが表示される', () => {
    render(<SignUpPage />)
    expect(screen.getByText('新規登録', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '新規登録' })).toBeInTheDocument()
  })

  it('全フィールドが空の場合は新規登録ボタンが無効', () => {
    render(<SignUpPage />)
    const button = screen.getByRole('button', { name: '新規登録' })
    expect(button).toBeDisabled()
  })

  it('表示名のみ入力では新規登録ボタンが無効', async () => {
    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    expect(screen.getByRole('button', { name: '新規登録' })).toBeDisabled()
  })

  it('メールアドレスが無効な場合は新規登録ボタンが無効', async () => {
    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    await user.type(screen.getByLabelText('メールアドレス'), 'not-an-email')
    await user.type(screen.getByLabelText('パスワード（8文字以上、英大小+数字）'), 'Password1')
    await user.type(screen.getByLabelText('パスワード（確認）'), 'Password1')
    expect(screen.getByRole('button', { name: '新規登録' })).toBeDisabled()
  })

  it('パスワードが不一致の場合は新規登録ボタンが無効', async () => {
    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    await user.type(screen.getByLabelText('メールアドレス'), 'test@example.com')
    await user.type(screen.getByLabelText('パスワード（8文字以上、英大小+数字）'), 'Password1')
    await user.type(screen.getByLabelText('パスワード（確認）'), 'Different1')
    expect(screen.getByRole('button', { name: '新規登録' })).toBeDisabled()
  })

  it('パスワード確認が空の場合は新規登録ボタンが無効', async () => {
    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    await user.type(screen.getByLabelText('メールアドレス'), 'test@example.com')
    await user.type(screen.getByLabelText('パスワード（8文字以上、英大小+数字）'), 'Password1')
    expect(screen.getByRole('button', { name: '新規登録' })).toBeDisabled()
  })

  it('全フィールドが有効な場合は新規登録ボタンが有効', async () => {
    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    await user.type(screen.getByLabelText('メールアドレス'), 'test@example.com')
    await user.type(screen.getByLabelText('パスワード（8文字以上、英大小+数字）'), 'Password1')
    await user.type(screen.getByLabelText('パスワード（確認）'), 'Password1')
    expect(screen.getByRole('button', { name: '新規登録' })).not.toBeDisabled()
  })

  it('有効な入力でsignUpが呼ばれる', async () => {
    const mockSignUp = vi.fn().mockResolvedValue(undefined)
    useAuthStore.setState({ signUp: mockSignUp } as never)

    const { user } = render(<SignUpPage />)
    await user.type(screen.getByLabelText('表示名'), 'テストユーザー')
    await user.type(screen.getByLabelText('メールアドレス'), 'test@example.com')
    await user.type(screen.getByLabelText('パスワード（8文字以上、英大小+数字）'), 'Password1')
    await user.type(screen.getByLabelText('パスワード（確認）'), 'Password1')
    await user.click(screen.getByRole('button', { name: '新規登録' }))
    expect(mockSignUp).toHaveBeenCalledWith('test@example.com', 'Password1', 'テストユーザー', '')
  })

  it('ストアからのエラーメッセージが表示される', () => {
    useAuthStore.setState({ error: 'このメールアドレスは既に登録されています' })
    render(<SignUpPage />)
    expect(screen.getByText('このメールアドレスは既に登録されています')).toBeInTheDocument()
  })

  it('ログインリンクが表示される', () => {
    render(<SignUpPage />)
    expect(screen.getByRole('link', { name: 'ログイン' })).toBeInTheDocument()
  })
})
