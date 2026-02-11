import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { Toast } from '../common/Toast';
import { CookieConsentBanner } from '../common/CookieConsentBanner';
import { LossLimitAlert } from '../loss-limit/LossLimitAlert';
import { useAuthStore } from '../../stores/authStore';
import { useLossLimitStore } from '../../stores/lossLimitStore';

export function Layout() {
  const { isAuthenticated } = useAuthStore();
  const { fetchLossLimit } = useLossLimitStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchLossLimit();
    }
  }, [isAuthenticated, fetchLossLimit]);

  return (
    <>
      <Header />
      <LossLimitAlert />
      <main>
        <Outlet />
      </main>
      <BottomNav />
      <CookieConsentBanner />
      <Toast />
    </>
  );
}
