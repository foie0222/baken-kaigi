import { describe, it, expect } from 'vitest'
import { render, screen } from '../test/utils'
import { HelpPage } from './HelpPage'

describe('HelpPage', () => {
  it('タイトルが表示される', () => {
    render(<HelpPage />)
    expect(screen.getByText('ヘルプ')).toBeInTheDocument()
  })

  it('全セクションが表示される', () => {
    render(<HelpPage />)
    expect(screen.getByText('馬券会議とは')).toBeInTheDocument()
    expect(screen.getByText('基本的な使い方')).toBeInTheDocument()
    expect(screen.getByText('AI分析提案について')).toBeInTheDocument()
    expect(screen.getByText('IPAT連携について')).toBeInTheDocument()
    expect(screen.getByText('負け額限度額について')).toBeInTheDocument()
    expect(screen.getByText('お問い合わせ')).toBeInTheDocument()
  })

  it('戻るボタンが表示される', () => {
    render(<HelpPage />)
    expect(screen.getByText(/戻る/)).toBeInTheDocument()
  })
})
