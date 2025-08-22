// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom'

// Mock DOM environment for React components
import { TextEncoder, TextDecoder } from 'util'
Object.assign(global, { TextDecoder, TextEncoder })

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

// Mock WebSocket
global.WebSocket = class WebSocket {
  url: string
  readyState: number = 1
  
  constructor(url: string) {
    this.url = url
  }
  
  send() {}
  close() {}
  addEventListener() {}
  removeEventListener() {}
} as typeof WebSocket

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