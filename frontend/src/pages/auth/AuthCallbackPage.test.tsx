import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../../test/utils';
import { AuthCallbackPage } from './AuthCallbackPage';
import { useAuthStore } from '../../stores/authStore';

// Hub モック
type HubCallback = (data: { payload: { event: string } }) => void;
let hubCallback: HubCallback | null = null;
const mockUnsubscribe = vi.fn();

vi.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: vi.fn((_channel: string, callback: HubCallback) => {
      hubCallback = callback;
      return mockUnsubscribe;
    }),
  },
}));

// react-router-dom のナビゲーション追跡
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('AuthCallbackPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
    hubCallback = null;
  });

  it('認証処理中のメッセージを表示する', () => {
    render(<AuthCallbackPage />);
    expect(screen.getByText('認証処理中...')).toBeInTheDocument();
  });

  it('トークン交換完了済みの新規OAuthユーザーを登録画面に遷移させる', async () => {
    // checkAuth が成功し、displayName が未設定のユーザーを返す
    useAuthStore.setState({
      checkAuth: vi.fn(async () => {
        useAuthStore.setState({
          user: { userId: 'user-123', email: 'test@example.com', displayName: '' },
          isAuthenticated: true,
          isLoading: false,
        });
      }),
    });

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/signup/age', {
        replace: true,
        state: { oauthUser: true },
      });
    });
  });

  it('トークン交換完了済みの既存ユーザーをホームに遷移させる', async () => {
    useAuthStore.setState({
      checkAuth: vi.fn(async () => {
        useAuthStore.setState({
          user: { userId: 'user-123', email: 'test@example.com', displayName: 'テスト' },
          isAuthenticated: true,
          isLoading: false,
        });
      }),
    });

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });
  });

  it('トークン交換未完了の場合、Hubイベントを待って新規ユーザーを登録画面に遷移させる', async () => {
    let callCount = 0;
    useAuthStore.setState({
      checkAuth: vi.fn(async () => {
        callCount++;
        if (callCount === 1) {
          // 1回目: トークン交換未完了、user は null のまま
          useAuthStore.setState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
        } else {
          // 2回目: トークン交換完了後
          useAuthStore.setState({
            user: { userId: 'user-123', email: 'test@example.com', displayName: '' },
            isAuthenticated: true,
            isLoading: false,
          });
        }
      }),
    });

    render(<AuthCallbackPage />);

    // 初回の processAuth では user が null なので遷移しない
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    // Hub の signInWithRedirect イベントを発火
    hubCallback?.({ payload: { event: 'signInWithRedirect' } });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/signup/age', {
        replace: true,
        state: { oauthUser: true },
      });
    });
  });

  it('OAuth失敗時にログインページへ遷移する', async () => {
    useAuthStore.setState({
      checkAuth: vi.fn(async () => {
        useAuthStore.setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }),
    });

    render(<AuthCallbackPage />);

    // Hub の signInWithRedirect_failure イベントを発火
    hubCallback?.({ payload: { event: 'signInWithRedirect_failure' } });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
    });
  });

  it('アンマウント時にHubリスナーとタイムアウトがクリーンアップされる', () => {
    const { unmount } = render(<AuthCallbackPage />);
    unmount();
    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});
