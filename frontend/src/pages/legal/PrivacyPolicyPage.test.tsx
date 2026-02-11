import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { PrivacyPolicyPage } from './PrivacyPolicyPage'
import { PRIVACY_VERSION } from '../../constants/legal'

describe('PrivacyPolicyPage', () => {
  it('タイトルが表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText('プライバシーポリシー')).toBeInTheDocument()
  })

  it('バージョン情報が表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(new RegExp(`バージョン ${PRIVACY_VERSION.version}`))).toBeInTheDocument()
  })

  it('全セクションが表示される', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText('1. 個人情報の収集')).toBeInTheDocument()
    expect(screen.getByText('2. 利用目的')).toBeInTheDocument()
    expect(screen.getByText('3. 第三者提供')).toBeInTheDocument()
    expect(screen.getByText('4. 外部サービスの利用')).toBeInTheDocument()
    expect(screen.getByText('5. Cookieの利用')).toBeInTheDocument()
    expect(screen.getByText('6. 保管と安全管理')).toBeInTheDocument()
    expect(screen.getByText('7. データの保持期間')).toBeInTheDocument()
    expect(screen.getByText('8. 開示・訂正・削除')).toBeInTheDocument()
    expect(screen.getByText('9. プライバシーポリシーの変更')).toBeInTheDocument()
    expect(screen.getByText('10. お問い合わせ')).toBeInTheDocument()
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

  it('収集する個人情報の具体的な項目が記載されている', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getAllByText(/メールアドレス/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/生年月日/).length).toBeGreaterThanOrEqual(1)
  })

  it('外部サービスの記載がある', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(/Google認証/)).toBeInTheDocument()
    expect(screen.getByText(/Appleでサインイン/)).toBeInTheDocument()
    expect(screen.getByText(/Amazon Web Services/)).toBeInTheDocument()
  })

  it('Cognito認証情報の取り扱いが記載されている', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(/Amazon Cognito/)).toBeInTheDocument()
  })

  it('DynamoDBデータの保持期間が記載されている', () => {
    render(<PrivacyPolicyPage />)
    expect(screen.getByText(/Amazon DynamoDB/)).toBeInTheDocument()
    expect(screen.getByText(/アカウント削除後30日以内に完全削除/)).toBeInTheDocument()
  })
})
