import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { PrivacyPolicyPage } from './PrivacyPolicyPage'

describe('PrivacyPolicyPage', () => {
  it('タイトルが表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText('プライバシーポリシー')).toBeInTheDocument()
  })

  it('バージョン情報が表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(/バージョン 1\.0\.0/)).toBeInTheDocument()
  })

  it('全セクションが表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText('1. 個人情報の収集')).toBeInTheDocument()
    expect(screen.getByText('2. 利用目的')).toBeInTheDocument()
    expect(screen.getByText('3. 第三者提供')).toBeInTheDocument()
    expect(screen.getByText('4. Cookieの利用')).toBeInTheDocument()
    expect(screen.getByText('5. 保管と安全管理')).toBeInTheDocument()
    expect(screen.getByText('6. 開示・訂正・削除')).toBeInTheDocument()
    expect(screen.getByText('7. お問い合わせ')).toBeInTheDocument()
  })

  it('Cookieポリシーへのリンクが表示される', () => {
    render(<PrivacyPolicyPage />)
    const link = screen.getByText('Cookieポリシー')
    expect(link).toBeInTheDocument()
    expect(link.closest('a')).toHaveAttribute('href', '/cookie-policy')
  })

  it('戻るボタンが表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(/戻る/)).toBeInTheDocument()
  })
})
