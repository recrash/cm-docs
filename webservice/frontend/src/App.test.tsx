import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import React from 'react'
import App from './App'

// Mock MainPage
vi.mock('./pages/MainPage', () => ({
  default: function MainPage() {
    return <div data-testid="main-page">Main Page</div>
  }
}))

// Mock router to render MainPage
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Routes: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Route: ({ element }: { element: React.ReactNode }) => element,
}))

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByText('🤖 테스트 시나리오 자동 생성기')).toBeInTheDocument()
  })

  it('renders the main page', () => {
    render(<App />)
    expect(screen.getByTestId('main-page')).toBeInTheDocument()
  })
})