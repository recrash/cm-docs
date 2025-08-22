// jest-dom adds custom matchers for asserting on DOM nodes (works with Vitest too).
import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Setup DOM environment properly
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock window.location for browser environment
Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    port: '3000',
    assign: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(),
  },
  writable: true,
})

// Mock WebSocket
global.WebSocket = class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3
  
  url: string
  readyState: number = 1
  
  constructor(url: string) {
    this.url = url
  }
  
  send() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
} as unknown as typeof WebSocket

// Mock console warnings
const originalWarn = console.warn
beforeAll(() => {
  console.warn = (message: string) => {
    if (message.includes('Warning:')) return
    originalWarn(message)
  }
})

afterAll(() => {
  console.warn = originalWarn
})