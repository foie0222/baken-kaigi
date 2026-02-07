import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { TermsPage } from './TermsPage'

describe('TermsPage', () => {
  it('タイトルが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText('利用規約')).toBeInTheDocument()
  })

  it('バージョン情報が表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText(/バージョン 1\.0\.0/)).toBeInTheDocument()
  })

  it('全セクションが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText('第1条（総則）')).toBeInTheDocument()
    expect(screen.getByText('第2条（定義）')).toBeInTheDocument()
    expect(screen.getByText('第3条（利用登録）')).toBeInTheDocument()
    expect(screen.getByText('第4条（禁止事項）')).toBeInTheDocument()
    expect(screen.getByText('第5条（免責事項）')).toBeInTheDocument()
    expect(screen.getByText('第6条（規約の変更）')).toBeInTheDocument()
    expect(screen.getByText('第7条（準拠法・裁判管轄）')).toBeInTheDocument()
  })

  it('戻るボタンが表示される', () => {
    render(<TermsPage />)
    expect(screen.getByText(/戻る/)).toBeInTheDocument()
  })

  it('プレースホルダーテキストが表示される', () => {
    render(<TermsPage />)
    const placeholders = screen.getAllByText('※ 法務確認後に正式な内容を掲載予定')
    expect(placeholders.length).toBeGreaterThanOrEqual(1)
  })
})
