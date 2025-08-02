// jest-dom adds custom jest matchers for asserting on DOM nodes.
import '@testing-library/jest-dom'

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
} as any

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