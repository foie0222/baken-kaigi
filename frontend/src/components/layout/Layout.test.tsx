import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { Layout } from './Layout'

describe('Layout', () => {
  it('ヘッダーとボトムナビが表示される', () => {
    render(<Layout />)

    expect(screen.getByText('馬券会議')).toBeInTheDocument()
    expect(screen.getByText('レース')).toBeInTheDocument()
  })

  it('ギャンブル依存症相談窓口リンクが表示されない', () => {
    render(<Layout />)

    expect(screen.queryByText(/ギャンブル依存症相談窓口/)).not.toBeInTheDocument()
  })
})
