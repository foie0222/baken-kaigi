import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { CookiePolicyPage } from './CookiePolicyPage'
import { COOKIE_POLICY_VERSION } from '../../constants/legal'

describe('CookiePolicyPage', () => {
  it('タイトルが表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText('Cookieポリシー')).toBeInTheDocument()
  })

  it('バージョン情報が表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText(new RegExp(`バージョン ${COOKIE_POLICY_VERSION.version}`))).toBeInTheDocument()
  })

  it('Cookieとはセクションが表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText('Cookieとは')).toBeInTheDocument()
  })

  it('Cookieの種類セクションが表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText('使用するCookieの種類')).toBeInTheDocument()
    expect(screen.getByText('必須Cookie')).toBeInTheDocument()
    expect(screen.getByText('分析Cookie')).toBeInTheDocument()
    expect(screen.getByText('マーケティングCookie')).toBeInTheDocument()
  })

  it('管理方法セクションが表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText('Cookieの管理方法')).toBeInTheDocument()
  })

  it('戻るボタンが表示される', () => {
    render(<CookiePolicyPage />)
    expect(screen.getByText(/戻る/)).toBeInTheDocument()
  })
})
