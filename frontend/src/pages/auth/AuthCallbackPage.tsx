import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Hub } from 'aws-amplify/utils';
import { useAuthStore } from '../../stores/authStore';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const checkAuth = useAuthStore((state) => state.checkAuth);
  const handled = useRef(false);

  useEffect(() => {
    const processAuth = async () => {
      if (handled.current) return;
      try {
        await checkAuth();
        const user = useAuthStore.getState().user;
        if (!user) return;
        handled.current = true;
        if (!user.displayName) {
          navigate('/signup/age', { replace: true, state: { oauthUser: true } });
        } else {
          navigate('/', { replace: true });
        }
      } catch {
        // トークン交換未完了の場合、Hubイベントを待つ
      }
    };

    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      if (handled.current) return;
      if (payload.event === 'signInWithRedirect') {
        processAuth();
      }
      if (payload.event === 'signInWithRedirect_failure') {
        handled.current = true;
        navigate('/login', { replace: true });
      }
    });

    // トークン交換が既に完了している場合に備えて即座に試行
    processAuth();

    // タイムアウト: 10秒以内にOAuth完了しなければログインに戻す
    const timeout = setTimeout(() => {
      if (!handled.current) {
        handled.current = true;
        navigate('/login', { replace: true });
      }
    }, 10000);

    return () => {
      handled.current = true;
      unsubscribe();
      clearTimeout(timeout);
    };
  }, [checkAuth, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: 40 }}>
      <p>認証処理中...</p>
    </div>
  );
}
