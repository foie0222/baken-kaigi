import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/utils'
import { ProposalCard } from './ProposalCard'
import type { ProposedBet } from '../../types'

const mockBet: ProposedBet = {
  bet_type: 'quinella',
  horse_numbers: [1, 2],
  bet_display: '1-2',
  amount: 1000,
  bet_count: 1,
  confidence: 'high',
  expected_value: 1.2,
  composite_odds: 5.0,
  reasoning: 'テスト根拠テキスト',
}

describe('ProposalCard', () => {
  it('買い目情報が表示される', () => {
    render(
      <ProposalCard bet={mockBet} onAddToCart={vi.fn()} isAdded={false} />
    )

    expect(screen.getByText('1-2')).toBeInTheDocument()
    expect(screen.getByText('テスト根拠テキスト')).toBeInTheDocument()
    expect(screen.getByText('信頼度: 高')).toBeInTheDocument()
  })

  it('カートに追加ボタンが動作する', async () => {
    const onAddToCart = vi.fn()
    const { user } = render(
      <ProposalCard bet={mockBet} onAddToCart={onAddToCart} isAdded={false} />
    )

    await user.click(screen.getByText('カートに追加'))
    expect(onAddToCart).toHaveBeenCalledTimes(1)
  })

  it('追加済みの場合ボタンがdisabledになる', () => {
    render(
      <ProposalCard bet={mockBet} onAddToCart={vi.fn()} isAdded={true} />
    )

    const button = screen.getByText('追加済み')
    expect(button).toBeDisabled()
  })

  it('オッズが0の場合は未確定と表示される', () => {
    const betWithZeroOdds: ProposedBet = { ...mockBet, composite_odds: 0, expected_value: 0 }
    render(
      <ProposalCard bet={betWithZeroOdds} onAddToCart={vi.fn()} isAdded={false} />
    )

    expect(screen.getByText(/推定オッズ:.*未確定/)).toBeInTheDocument()
    expect(screen.getByText(/期待値:.*未確定/)).toBeInTheDocument()
  })

  it('オッズが1.0未満の小さな正の値の場合は未確定と表示される', () => {
    const betWithTinyOdds: ProposedBet = { ...mockBet, composite_odds: 0.01, expected_value: 0.005 }
    render(
      <ProposalCard bet={betWithTinyOdds} onAddToCart={vi.fn()} isAdded={false} />
    )

    expect(screen.getByText(/推定オッズ:.*未確定/)).toBeInTheDocument()
    expect(screen.getByText(/期待値:.*未確定/)).toBeInTheDocument()
  })

  it('オッズがある場合は数値が表示される', () => {
    render(
      <ProposalCard bet={mockBet} onAddToCart={vi.fn()} isAdded={false} />
    )

    expect(screen.getByText(/5\.0倍/)).toBeInTheDocument()
    expect(screen.getByText(/1\.20/)).toBeInTheDocument()
  })
})
