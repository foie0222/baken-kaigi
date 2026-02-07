import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { COOKIE_POLICY_VERSION } from '../constants/legal';

interface CookieCategories {
  essential: true;
  analytics: boolean;
  marketing: boolean;
}

interface CookieConsentState {
  consent: CookieCategories | null;
  consentTimestamp: string | null;
  consentVersion: string | null;
  acceptAll: () => void;
  rejectOptional: () => void;
  updateConsent: (categories: Omit<CookieCategories, 'essential'>) => void;
  resetConsent: () => void;
}

export const useCookieConsentStore = create<CookieConsentState>()(
  persist(
    (set) => ({
      consent: null,
      consentTimestamp: null,
      consentVersion: null,

      acceptAll: () => {
        set({
          consent: { essential: true, analytics: true, marketing: true },
          consentTimestamp: new Date().toISOString(),
          consentVersion: COOKIE_POLICY_VERSION.version,
        });
      },

      rejectOptional: () => {
        set({
          consent: { essential: true, analytics: false, marketing: false },
          consentTimestamp: new Date().toISOString(),
          consentVersion: COOKIE_POLICY_VERSION.version,
        });
      },

      updateConsent: (categories) => {
        set({
          consent: { essential: true, ...categories },
          consentTimestamp: new Date().toISOString(),
          consentVersion: COOKIE_POLICY_VERSION.version,
        });
      },

      resetConsent: () => {
        set({
          consent: null,
          consentTimestamp: null,
          consentVersion: null,
        });
      },
    }),
    {
      name: 'baken-kaigi-cookie-consent',
    }
  )
);
