/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vitest/config'
import { defineConfig as defineViteConfig } from 'vite'
import react from '@vitejs/plugin-react'

const viteConfig = defineViteConfig({
  plugins: [react()],
})

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/setupTests.ts'],
      globals: true,
      css: false,
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/e2e/**'
      ],
      environmentOptions: {
        jsdom: {
          resources: 'usable'
        }
      },
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        exclude: [
          'node_modules/',
          'src/setupTests.ts',
          'src/main.tsx',
          'src/vite-env.d.ts',
          '**/*.d.ts',
          'coverage/**',
          'dist/**',
        ]
      }
    }
  }),
)