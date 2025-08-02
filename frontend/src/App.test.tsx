import React from 'react'
import { render, screen } from '@testing-library/react'
import App from './App'

// Mock router
jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Routes: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Route: () => <div>Route Component</div>,
}))

// Mock MainPage
jest.mock('./pages/MainPage', () => {
  return function MainPage() {
    return <div data-testid="main-page">Main Page</div>
  }
})

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