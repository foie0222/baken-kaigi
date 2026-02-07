import { describe, it, expect, beforeEach } from 'vitest'
import { useCookieConsentStore } from './cookieConsentStore'
import { COOKIE_POLICY_VERSION } from '../constants/legal'

describe('cookieConsentStore', () => {
  beforeEach(() => {
    useCookieConsentStore.setState({
      consent: null,
      consentTimestamp: null,
      consentVersion: null,
    })
  })

  describe('初期状態', () => {
    it('consentがnullである', () => {
      const state = useCookieConsentStore.getState()
      expect(state.consent).toBeNull()
    })

    it('consentTimestampがnullである', () => {
      const state = useCookieConsentStore.getState()
      expect(state.consentTimestamp).toBeNull()
    })

    it('consentVersionがnullである', () => {
      const state = useCookieConsentStore.getState()
      expect(state.consentVersion).toBeNull()
    })
  })

  describe('acceptAll', () => {
    it('すべてのカテゴリをtrueに設定する', () => {
      useCookieConsentStore.getState().acceptAll()

      const state = useCookieConsentStore.getState()
      expect(state.consent).toEqual({
        essential: true,
        analytics: true,
        marketing: true,
      })
    })

    it('タイムスタンプが設定される', () => {
      const before = new Date().toISOString()
      useCookieConsentStore.getState().acceptAll()
      const after = new Date().toISOString()

      const state = useCookieConsentStore.getState()
      expect(state.consentTimestamp).not.toBeNull()
      expect(state.consentTimestamp! >= before).toBe(true)
      expect(state.consentTimestamp! <= after).toBe(true)
    })

    it('バージョンが設定される', () => {
      useCookieConsentStore.getState().acceptAll()

      const state = useCookieConsentStore.getState()
      expect(state.consentVersion).toBe(COOKIE_POLICY_VERSION.version)
    })
  })

  describe('rejectOptional', () => {
    it('essentialのみtrueで他はfalseに設定する', () => {
      useCookieConsentStore.getState().rejectOptional()

      const state = useCookieConsentStore.getState()
      expect(state.consent).toEqual({
        essential: true,
        analytics: false,
        marketing: false,
      })
    })

    it('タイムスタンプが設定される', () => {
      useCookieConsentStore.getState().rejectOptional()

      const state = useCookieConsentStore.getState()
      expect(state.consentTimestamp).not.toBeNull()
    })

    it('バージョンが設定される', () => {
      useCookieConsentStore.getState().rejectOptional()

      const state = useCookieConsentStore.getState()
      expect(state.consentVersion).toBe(COOKIE_POLICY_VERSION.version)
    })
  })

  describe('updateConsent', () => {
    it('analyticsのみtrueに設定できる', () => {
      useCookieConsentStore.getState().updateConsent({ analytics: true, marketing: false })

      const state = useCookieConsentStore.getState()
      expect(state.consent).toEqual({
        essential: true,
        analytics: true,
        marketing: false,
      })
    })

    it('marketingのみtrueに設定できる', () => {
      useCookieConsentStore.getState().updateConsent({ analytics: false, marketing: true })

      const state = useCookieConsentStore.getState()
      expect(state.consent).toEqual({
        essential: true,
        analytics: false,
        marketing: true,
      })
    })

    it('essentialは常にtrueである', () => {
      useCookieConsentStore.getState().updateConsent({ analytics: false, marketing: false })

      const state = useCookieConsentStore.getState()
      expect(state.consent!.essential).toBe(true)
    })

    it('タイムスタンプとバージョンが設定される', () => {
      useCookieConsentStore.getState().updateConsent({ analytics: true, marketing: true })

      const state = useCookieConsentStore.getState()
      expect(state.consentTimestamp).not.toBeNull()
      expect(state.consentVersion).toBe(COOKIE_POLICY_VERSION.version)
    })
  })

  describe('resetConsent', () => {
    it('すべての状態をnullにリセットする', () => {
      useCookieConsentStore.getState().acceptAll()
      useCookieConsentStore.getState().resetConsent()

      const state = useCookieConsentStore.getState()
      expect(state.consent).toBeNull()
      expect(state.consentTimestamp).toBeNull()
      expect(state.consentVersion).toBeNull()
    })

    it('rejectOptional後にリセットできる', () => {
      useCookieConsentStore.getState().rejectOptional()
      useCookieConsentStore.getState().resetConsent()

      const state = useCookieConsentStore.getState()
      expect(state.consent).toBeNull()
    })
  })
})
