import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Layout } from './components/layout/Layout';
import { RacesPage } from './pages/RacesPage';
import { RaceDetailPage } from './pages/RaceDetailPage';
import { CartPage } from './pages/CartPage';
import { BetReviewPage } from './pages/BetReviewPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoginPage } from './pages/auth/LoginPage';
import { SignUpPage } from './pages/auth/SignUpPage';
import { ConfirmSignUpPage } from './pages/auth/ConfirmSignUpPage';
import { AgeVerificationPage } from './pages/auth/AgeVerificationPage';
import { TermsAgreementPage } from './pages/auth/TermsAgreementPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage';
import { ProfilePage } from './pages/auth/ProfilePage';
import { ChangePasswordPage } from './pages/auth/ChangePasswordPage';
import { DeleteAccountPage } from './pages/auth/DeleteAccountPage';
import { AuthCallbackPage } from './pages/auth/AuthCallbackPage';
import { IpatSettingsPage } from './pages/IpatSettingsPage';
import { PurchaseConfirmPage } from './pages/PurchaseConfirmPage';
import { PurchaseHistoryPage } from './pages/PurchaseHistoryPage';
import { TermsPage } from './pages/legal/TermsPage';
import { PrivacyPolicyPage } from './pages/legal/PrivacyPolicyPage';
import { CookiePolicyPage } from './pages/legal/CookiePolicyPage';
import { HelpPage } from './pages/HelpPage';
import { OAuthProfilePage } from './pages/auth/OAuthProfilePage';
import { OnboardingPage } from './pages/OnboardingPage';
import { AuthGuard } from './components/auth/AuthGuard';
import { useAuthStore } from './stores/authStore';
import './styles/index.css';

function App() {
  const checkAuth = useAuthStore((state) => state.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* 認証不要ページ */}
          <Route index element={<RacesPage />} />
          <Route path="races/:raceId" element={<RaceDetailPage />} />
          <Route path="cart" element={<CartPage />} />
          <Route path="bet-review" element={<BetReviewPage />} />
          <Route path="consultation" element={<Navigate to="/bet-review" replace />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="privacy" element={<PrivacyPolicyPage />} />
          <Route path="cookie-policy" element={<CookiePolicyPage />} />
          <Route path="help" element={<HelpPage />} />

          {/* 認証ページ */}
          <Route path="login" element={<LoginPage />} />
          <Route path="signup/age" element={<AgeVerificationPage />} />
          <Route path="signup/terms" element={<TermsAgreementPage />} />
          <Route path="signup" element={<SignUpPage />} />
          <Route path="signup/confirm" element={<ConfirmSignUpPage />} />
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
          <Route path="reset-password" element={<ResetPasswordPage />} />
          <Route path="auth/callback" element={<AuthCallbackPage />} />
          <Route path="oauth/complete" element={<OAuthProfilePage />} />

          {/* 認証必須ページ */}
          <Route path="profile" element={<AuthGuard><ProfilePage /></AuthGuard>} />
          <Route path="change-password" element={<AuthGuard><ChangePasswordPage /></AuthGuard>} />
          <Route path="delete-account" element={<AuthGuard><DeleteAccountPage /></AuthGuard>} />
          <Route path="onboarding" element={<AuthGuard><OnboardingPage /></AuthGuard>} />
          <Route path="dashboard" element={<AuthGuard><DashboardPage /></AuthGuard>} />
          <Route path="history" element={<AuthGuard><HistoryPage /></AuthGuard>} />
          <Route path="purchase/confirm" element={<AuthGuard><PurchaseConfirmPage /></AuthGuard>} />
          <Route path="purchase/history" element={<AuthGuard><PurchaseHistoryPage /></AuthGuard>} />
          <Route path="settings/ipat" element={<AuthGuard><IpatSettingsPage /></AuthGuard>} />

          {/* 存在しないパスはホームにリダイレクト */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
