import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '../../test/utils'
import { CookieConsentBanner } from './CookieConsentBanner'
import { useCookieConsentStore } from '../../stores/cookieConsentStore'

describe('CookieConsentBanner', () => {
  beforeEach(() => {
    useCookieConsentStore.setState({
      consent: null,
      consentTimestamp: null,
      consentVersion: null,
    })
  })

  it('consentがnullの場合にバナーが表示される', () => {
    render(<CookieConsentBanner />)
    expect(screen.getByText(/本サービスではCookieを使用しています/)).toBeInTheDocument()
  })

  it('consentが設定済みの場合はバナーが表示されない', () => {
    useCookieConsentStore.setState({
      consent: { essential: true, analytics: false, marketing: false },
      consentTimestamp: new Date().toISOString(),
      consentVersion: '1.0.0',
    })

    const { container } = render(<CookieConsentBanner />)
    expect(container.firstChild).toBeNull()
  })

  it('3つのボタンが表示される', () => {
    render(<CookieConsentBanner />)
    expect(screen.getByText('詳細設定')).toBeInTheDocument()
    expect(screen.getByText('必要なもののみ')).toBeInTheDocument()
    expect(screen.getByText('すべて許可')).toBeInTheDocument()
  })

  it('Cookieポリシーへのリンクが表示される', () => {
    render(<CookieConsentBanner />)
    const link = screen.getByText('Cookieポリシー')
    expect(link.closest('a')).toHaveAttribute('href', '/cookie-policy')
  })

  it('すべて許可をクリックするとバナーが非表示になる', async () => {
    const { user } = render(<CookieConsentBanner />)
    await user.click(screen.getByText('すべて許可'))

    const state = useCookieConsentStore.getState()
    expect(state.consent).toEqual({
      essential: true,
      analytics: true,
      marketing: true,
    })
  })

  it('必要なもののみをクリックするとオプションが拒否される', async () => {
    const { user } = render(<CookieConsentBanner />)
    await user.click(screen.getByText('必要なもののみ'))

    const state = useCookieConsentStore.getState()
    expect(state.consent).toEqual({
      essential: true,
      analytics: false,
      marketing: false,
    })
  })

  it('詳細設定をクリックすると詳細パネルが表示される', async () => {
    const { user } = render(<CookieConsentBanner />)
    await user.click(screen.getByText('詳細設定'))

    expect(screen.getByText('必須Cookie')).toBeInTheDocument()
    expect(screen.getByText('分析Cookie')).toBeInTheDocument()
    expect(screen.getByText('マーケティングCookie')).toBeInTheDocument()
    expect(screen.getByText('保存')).toBeInTheDocument()
  })

  it('詳細設定パネルで保存するとカスタム設定が保存される', async () => {
    const { user } = render(<CookieConsentBanner />)
    await user.click(screen.getByText('詳細設定'))
    await user.click(screen.getByText('保存'))

    const state = useCookieConsentStore.getState()
    expect(state.consent).toEqual({
      essential: true,
      analytics: false,
      marketing: false,
    })
  })

  it('トグルクリックで分析・マーケティングCookieの状態が切り替わる', async () => {
    const { user } = render(<CookieConsentBanner />)
    await user.click(screen.getByText('詳細設定'))

    const analyticsToggle = screen.getByLabelText('分析Cookie')
    const marketingToggle = screen.getByLabelText('マーケティングCookie')

    expect(analyticsToggle).not.toBeChecked()
    expect(marketingToggle).not.toBeChecked()

    await user.click(analyticsToggle)
    expect(analyticsToggle).toBeChecked()

    await user.click(marketingToggle)
    expect(marketingToggle).toBeChecked()

    await user.click(screen.getByText('保存'))
    const state = useCookieConsentStore.getState()
    expect(state.consent).toEqual({
      essential: true,
      analytics: true,
      marketing: true,
    })
  })
})
