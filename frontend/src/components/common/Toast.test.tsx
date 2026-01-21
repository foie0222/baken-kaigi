import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, act } from '../../test/utils'
import { Toast } from './Toast'
import { useAppStore } from '../../stores/appStore'

describe('Toast', () => {
  beforeEach(() => {
    // ストアをリセット
    useAppStore.setState({ toastMessage: null })
  })

  it('メッセージがない場合は何も表示しない', () => {
    const { container } = render(<Toast />)
    expect(container.firstChild).toBeNull()
  })

  it('メッセージがある場合に表示する', () => {
    useAppStore.setState({ toastMessage: 'テストメッセージ' })

    render(<Toast />)

    expect(screen.getByText('テストメッセージ')).toBeInTheDocument()
  })

  it('toastクラスが適用される', () => {
    useAppStore.setState({ toastMessage: '確認メッセージ' })

    render(<Toast />)

    const toast = screen.getByText('確認メッセージ')
    expect(toast).toHaveClass('toast')
  })

  it('メッセージが変更されると表示が更新される', () => {
    useAppStore.setState({ toastMessage: '最初のメッセージ' })

    const { rerender } = render(<Toast />)
    expect(screen.getByText('最初のメッセージ')).toBeInTheDocument()

    act(() => {
      useAppStore.setState({ toastMessage: '更新されたメッセージ' })
    })
    rerender(<Toast />)

    expect(screen.queryByText('最初のメッセージ')).not.toBeInTheDocument()
    expect(screen.getByText('更新されたメッセージ')).toBeInTheDocument()
  })
})
