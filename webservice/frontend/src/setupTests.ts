// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom'

// Mock DOM environment for React components
import { TextEncoder, TextDecoder } from 'util'
Object.assign(global, { TextDecoder, TextEncoder })

// Mock import.meta.env for Vite environment variables
Object.defineProperty(global, 'import', {
  value: {
    meta: {
      env: {
        DEV: false,
        MODE: 'test',
        PROD: true,
        VITE_API_URL: 'http://localhost:8000',
      }
    }
  }
})

// Setup DOM environment properly
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock window.location for browser environment
Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    port: '3000',
    assign: jest.fn(),
    replace: jest.fn(),
    reload: jest.fn(),
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