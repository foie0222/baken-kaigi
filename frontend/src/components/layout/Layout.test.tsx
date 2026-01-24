import { describe, it, expect } from 'vitest'
import { render, screen } from '../../test/utils'
import { Layout } from './Layout'

describe('Layout', () => {
  describe('HelpLink', () => {
    it('ギャンブル依存症相談窓口リンクが表示される', () => {
      render(<Layout />)

      const helpLink = screen.getByRole('link', { name: /ギャンブル依存症の相談窓口へ/i })
      expect(helpLink).toBeInTheDocument()
    })

    it('リンクが厚生労働省のページに設定されている', () => {
      render(<Layout />)

      const helpLink = screen.getByRole('link', { name: /ギャンブル依存症の相談窓口へ/i })
      expect(helpLink).toHaveAttribute(
        'href',
        'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000070789.html'
      )
    })

    it('リンクが新しいタブで開く設定になっている', () => {
      render(<Layout />)

      const helpLink = screen.getByRole('link', { name: /ギャンブル依存症の相談窓口へ/i })
      expect(helpLink).toHaveAttribute('target', '_blank')
      expect(helpLink).toHaveAttribute('rel', 'noopener noreferrer')
    })

    it('aria-label属性で新しいタブで開くことが明示されている', () => {
      render(<Layout />)

      const helpLink = screen.getByRole('link', { name: /ギャンブル依存症の相談窓口へ/i })
      expect(helpLink).toHaveAttribute(
        'aria-label',
        'ギャンブル依存症の相談窓口へ（新しいタブで開く）'
      )
    })
  })
})
