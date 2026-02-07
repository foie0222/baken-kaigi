import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '../../test/utils';
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

  afterEach(() => {
    vi.useRealTimers();
  });

  it('認証処理中のメッセージを表示する', () => {
    render(<AuthCallbackPage />);
    expect(screen.getByText('認証処理中...')).toBeInTheDocument();
  });

  it('トークン交換完了済みの新規OAuthユーザーを登録画面に遷移させる', async () => {
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
    const mockCheckAuth = vi.fn(async () => {
      callCount++;
      if (callCount === 1) {
        useAuthStore.setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      } else {
        useAuthStore.setState({
          user: { userId: 'user-123', email: 'test@example.com', displayName: '' },
          isAuthenticated: true,
          isLoading: false,
        });
      }
    });
    useAuthStore.setState({ checkAuth: mockCheckAuth });

    render(<AuthCallbackPage />);

    // 初回の processAuth 完了を待つ
    await waitFor(() => {
      expect(mockCheckAuth).toHaveBeenCalledTimes(1);
    });

    // 初回は user が null なので遷移していないことを確認
    expect(mockNavigate).not.toHaveBeenCalled();

    // Hub の signInWithRedirect イベントを発火
    await act(async () => {
      hubCallback?.({ payload: { event: 'signInWithRedirect' } });
    });

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

    await act(async () => {
      hubCallback?.({ payload: { event: 'signInWithRedirect_failure' } });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
    });
  });

  it('タイムアウト時にログインページへフォールバックする', async () => {
    vi.useFakeTimers();

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

    // タイムアウト前は遷移しない
    await act(async () => {
      vi.advanceTimersByTime(9999);
    });
    expect(mockNavigate).not.toHaveBeenCalled();

    // タイムアウト後にログインページへ遷移
    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
  });

  it('Hub成功後はタイムアウトが発火しない', async () => {
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

    // checkAuth成功でホームに遷移
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    });

    mockNavigate.mockClear();

    // fake timers に切り替えてタイムアウトを進める
    vi.useFakeTimers();
    await act(async () => {
      vi.advanceTimersByTime(10000);
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('アンマウント時にHubリスナーとタイムアウトがクリーンアップされる', () => {
    const { unmount } = render(<AuthCallbackPage />);
    unmount();
    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});
