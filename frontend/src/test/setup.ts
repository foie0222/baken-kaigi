import '@testing-library/jest-dom'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// React Testing Libraryのクリーンアップを各テスト後に実行
afterEach(() => {
  cleanup()
})
