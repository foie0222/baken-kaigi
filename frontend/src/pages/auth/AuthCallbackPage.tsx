import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const checkAuth = useAuthStore((state) => state.checkAuth);

  useEffect(() => {
    const handleCallback = async () => {
      await checkAuth();
      navigate('/', { replace: true });
    };
    handleCallback();
  }, [checkAuth, navigate]);

  return (
    <div style={{ textAlign: 'center', padding: 40 }}>
      <p>認証処理中...</p>
    </div>
  );
}
