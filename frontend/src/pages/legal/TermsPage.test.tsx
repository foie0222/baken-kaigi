import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { TermsPage } from './TermsPage'
import { TERMS_VERSION } from '../../constants/legal'

describe('TermsPage', () => {
  it('タイトルが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText('利用規約')).toBeInTheDocument()
  })

  it('バージョン情報が表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText(new RegExp(`バージョン ${TERMS_VERSION.version}`))).toBeInTheDocument()
  })

  it('全セクションが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText('第1条（総則）')).toBeInTheDocument()
    expect(screen.getByText('第2条（定義）')).toBeInTheDocument()
    expect(screen.getByText('第3条（利用登録）')).toBeInTheDocument()
    expect(screen.getByText('第4条（アカウント管理）')).toBeInTheDocument()
    expect(screen.getByText('第5条（サービス内容）')).toBeInTheDocument()
    expect(screen.getByText('第6条（禁止事項）')).toBeInTheDocument()
    expect(screen.getByText('第7条（知的財産権）')).toBeInTheDocument()
    expect(screen.getByText('第8条（免責事項）')).toBeInTheDocument()
    expect(screen.getByText('第9条（利用制限・登録抹消）')).toBeInTheDocument()
    expect(screen.getByText('第10条（規約の変更）')).toBeInTheDocument()
    expect(screen.getByText('第11条（個人情報の取扱い）')).toBeInTheDocument()
    expect(screen.getByText('第12条（準拠法・裁判管轄）')).toBeInTheDocument()
  })

  it('戻るボタンが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText(/戻る/)).toBeInTheDocument()
  })

  it('免責事項に馬券購入の自己責任に関する記載がある', () => {
    render(<TermsPage />)
    const elements = screen.getAllByText(/的中や利益を保証するものではありません/)
    expect(elements.length).toBeGreaterThanOrEqual(1)
  })

  it('20歳以上の年齢制限に関する記載がある', () => {
    render(<TermsPage />)
    expect(screen.getByText(/20歳以上の方のみ利用登録が可能/)).toBeInTheDocument()
  })

  it('Google・Apple認証に関する記載がある', () => {
    render(<TermsPage />)
    expect(screen.getByText(/Googleアカウントまたは Appleアカウントによる認証/)).toBeInTheDocument()
  })
})
