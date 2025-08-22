// Jest setup for Vite environment
global.import = {
  meta: {
    env: {
      DEV: false,
      MODE: 'test',
      PROD: true,
      VITE_API_URL: 'http://localhost:8000',
    }
  }
}