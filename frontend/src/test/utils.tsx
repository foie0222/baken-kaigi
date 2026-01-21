import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import userEvent from '@testing-library/user-event'

// テスト用のラッパーコンポーネント
interface WrapperProps {
  children: ReactNode
}

function AllProviders({ children }: WrapperProps) {
  return <BrowserRouter>{children}</BrowserRouter>
}

// カスタムrender関数
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return {
    user: userEvent.setup(),
    ...render(ui, { wrapper: AllProviders, ...options }),
  }
}

// re-export everything
export * from '@testing-library/react'
export { customRender as render, userEvent }
