import { render, screen, cleanup } from '@testing-library/react'
import { vi, afterEach } from 'vitest'
import App from './App'

// Mock MainPage
vi.mock('./pages/MainPage', () => ({
  default: function MainPage() {
    return <div data-testid="main-page">Main Page</div>
  }
}))

// Mock router to render MainPage
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: any }) => <div>{children}</div>,
  Routes: ({ children }: { children: any }) => <div>{children}</div>,
  Route: ({ element }: { element: any }) => element,
}))

describe('App', () => {
  // 각 테스트 후 명시적으로 cleanup 수행
  afterEach(() => {
    cleanup()
  })

  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByText('🤖 테스트 시나리오 자동 생성기')).toBeInTheDocument()
  })

  it('renders the main page', () => {
    render(<App />)
    expect(screen.getByTestId('main-page')).toBeInTheDocument()
  })
})