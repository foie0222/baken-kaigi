import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '../../test/utils'
import { AuthGuard } from './AuthGuard'
import { useAuthStore } from '../../stores/authStore'

// authStoreの状態を直接設定するヘルパー
function setAuthState(overrides: Partial<ReturnType<typeof useAuthStore.getState>>) {
  useAuthStore.setState(overrides)
}

describe('AuthGuard', () => {
  beforeEach(() => {
    // 各テスト前にストアをリセット
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    })
  })

  it('ローディング中は「読み込み中...」を表示する', () => {
    setAuthState({ isLoading: true, isAuthenticated: false })

    render(
      <AuthGuard>
        <div>保護されたコンテンツ</div>
      </AuthGuard>
    )

    expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    expect(screen.queryByText('保護されたコンテンツ')).not.toBeInTheDocument()
  })

  it('認証済みの場合は子要素を表示する', () => {
    setAuthState({
      isAuthenticated: true,
      isLoading: false,
      user: { userId: 'test-id', email: 'test@example.com' },
    })

    render(
      <AuthGuard>
        <div>保護されたコンテンツ</div>
      </AuthGuard>
    )

    expect(screen.getByText('保護されたコンテンツ')).toBeInTheDocument()
  })

  it('未認証の場合は子要素を表示しない', () => {
    setAuthState({ isAuthenticated: false, isLoading: false })

    render(
      <AuthGuard>
        <div>保護されたコンテンツ</div>
      </AuthGuard>
    )

    expect(screen.queryByText('保護されたコンテンツ')).not.toBeInTheDocument()
  })
})
