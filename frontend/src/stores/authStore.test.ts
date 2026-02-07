import { describe, it, expect, vi, beforeEach } from 'vitest'

// authStoreより先にモックを定義
const mockGetCurrentUser = vi.fn()
const mockFetchAuthSession = vi.fn()
const mockSignUp = vi.fn()
const mockConfirmSignUp = vi.fn()
const mockSignIn = vi.fn()
const mockSignOut = vi.fn()
const mockResetPassword = vi.fn()
const mockConfirmResetPassword = vi.fn()
const mockUpdatePassword = vi.fn()
const mockDeleteUser = vi.fn()
const mockSignInWithRedirect = vi.fn()

vi.mock('aws-amplify/auth', () => ({
  getCurrentUser: (...args: unknown[]) => mockGetCurrentUser(...args),
  fetchAuthSession: (...args: unknown[]) => mockFetchAuthSession(...args),
  signUp: (...args: unknown[]) => mockSignUp(...args),
  confirmSignUp: (...args: unknown[]) => mockConfirmSignUp(...args),
  signIn: (...args: unknown[]) => mockSignIn(...args),
  signOut: (...args: unknown[]) => mockSignOut(...args),
  resetPassword: (...args: unknown[]) => mockResetPassword(...args),
  confirmResetPassword: (...args: unknown[]) => mockConfirmResetPassword(...args),
  updatePassword: (...args: unknown[]) => mockUpdatePassword(...args),
  deleteUser: (...args: unknown[]) => mockDeleteUser(...args),
  signInWithRedirect: (...args: unknown[]) => mockSignInWithRedirect(...args),
}))

import { useAuthStore } from './authStore'

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
    vi.clearAllMocks()
  })

  describe('初期状態', () => {
    it('初期状態が正しく設定されている', () => {
      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.isAuthenticated).toBe(false)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
    })
  })

  describe('clearError', () => {
    it('エラーをクリアできる', () => {
      useAuthStore.setState({ error: 'テストエラー' })
      expect(useAuthStore.getState().error).toBe('テストエラー')

      useAuthStore.getState().clearError()
      expect(useAuthStore.getState().error).toBeNull()
    })
  })

  describe('checkAuth', () => {
    it('認証済みユーザーの情報を取得する', async () => {
      mockGetCurrentUser.mockResolvedValueOnce({ userId: 'user-123', username: 'test' })
      mockFetchAuthSession.mockResolvedValueOnce({
        tokens: {
          idToken: {
            payload: {
              email: 'test@example.com',
              'custom:display_name': 'テストユーザー',
            },
          },
        },
      })

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user).toEqual({
        userId: 'user-123',
        email: 'test@example.com',
        displayName: 'テストユーザー',
      })
      expect(state.isLoading).toBe(false)
    })

    it('未認証の場合はユーザー情報をクリアする', async () => {
      mockGetCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'))

      await useAuthStore.getState().checkAuth()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
      expect(state.isLoading).toBe(false)
    })
  })

  describe('signUp', () => {
    it('サインアップが成功する', async () => {
      mockSignUp.mockResolvedValueOnce({})

      await useAuthStore.getState().signUp('test@example.com', 'Password123', 'テスト', '1990-01-01')

      const state = useAuthStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
      expect(mockSignUp).toHaveBeenCalledWith({
        username: 'test@example.com',
        password: 'Password123',
        options: {
          userAttributes: {
            email: 'test@example.com',
            birthdate: '1990-01-01',
            'custom:display_name': 'テスト',
          },
        },
      })
    })

    it('サインアップ失敗時にエラーが設定される', async () => {
      mockSignUp.mockRejectedValueOnce(new Error('User already exists'))

      await expect(
        useAuthStore.getState().signUp('test@example.com', 'Password123', 'テスト', '1990-01-01')
      ).rejects.toThrow('User already exists')

      const state = useAuthStore.getState()
      expect(state.isLoading).toBe(false)
      expect(state.error).toBe('User already exists')
    })
  })

  describe('signIn', () => {
    it('サインインが成功する', async () => {
      mockSignIn.mockResolvedValueOnce({})
      mockGetCurrentUser.mockResolvedValueOnce({ userId: 'user-123', username: 'test' })
      mockFetchAuthSession.mockResolvedValueOnce({
        tokens: {
          idToken: {
            payload: {
              'custom:display_name': 'テストユーザー',
            },
          },
        },
      })

      await useAuthStore.getState().signIn('test@example.com', 'Password123')

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(true)
      expect(state.user?.email).toBe('test@example.com')
      expect(state.user?.displayName).toBe('テストユーザー')
      expect(state.isLoading).toBe(false)
    })

    it('サインイン失敗時にエラーが設定される', async () => {
      mockSignIn.mockRejectedValueOnce(new Error('Incorrect username or password'))

      await expect(
        useAuthStore.getState().signIn('test@example.com', 'wrong')
      ).rejects.toThrow('Incorrect username or password')

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.error).toBe('Incorrect username or password')
    })
  })

  describe('signOut', () => {
    it('サインアウトが成功する', async () => {
      mockSignOut.mockResolvedValueOnce({})

      useAuthStore.setState({
        user: { userId: 'user-123', email: 'test@example.com' },
        isAuthenticated: true,
      })

      await useAuthStore.getState().signOut()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
      expect(state.isLoading).toBe(false)
    })
  })

  describe('confirmSignUp', () => {
    it('確認コードが正しく送信される', async () => {
      mockConfirmSignUp.mockResolvedValueOnce({})

      await useAuthStore.getState().confirmSignUp('test@example.com', '123456')

      expect(mockConfirmSignUp).toHaveBeenCalledWith({
        username: 'test@example.com',
        confirmationCode: '123456',
      })
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  describe('forgotPassword', () => {
    it('パスワードリセット要求が送信される', async () => {
      mockResetPassword.mockResolvedValueOnce({})

      await useAuthStore.getState().forgotPassword('test@example.com')

      expect(mockResetPassword).toHaveBeenCalledWith({ username: 'test@example.com' })
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  describe('changePassword', () => {
    it('パスワード変更が成功する', async () => {
      mockUpdatePassword.mockResolvedValueOnce({})

      await useAuthStore.getState().changePassword('OldPass123', 'NewPass456')

      expect(mockUpdatePassword).toHaveBeenCalledWith({
        oldPassword: 'OldPass123',
        newPassword: 'NewPass456',
      })
      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  describe('deleteAccount', () => {
    it('アカウント削除が成功する', async () => {
      mockDeleteUser.mockResolvedValueOnce({})

      useAuthStore.setState({
        user: { userId: 'user-123', email: 'test@example.com' },
        isAuthenticated: true,
      })

      await useAuthStore.getState().deleteAccount()

      const state = useAuthStore.getState()
      expect(state.isAuthenticated).toBe(false)
      expect(state.user).toBeNull()
    })
  })
})
