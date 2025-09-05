/**
 * v2 CLI 연동 워크플로우 E2E 테스트
 * 
 * 전체 사용자 워크플로우 테스트:
 * 1. 웹페이지 접속 (localhost:3000)
 * 2. 저장소 경로 입력
 * 3. "생성하기" 버튼 클릭
 * 4. Custom URL Protocol 호출 확인
 * 5. WebSocket 연결 및 진행 상황 확인
 * 6. 완료 후 결과 화면 전환 확인
 */

import { test, expect, Page } from '@playwright/test'

// 테스트 설정
const TEST_REPO_PATH = '/Users/recrash/Documents/Workspace/TestscenarioMaker'
const FRONTEND_URL = 'http://localhost:3000'
const BACKEND_URL = 'http://localhost:80'

test.describe('v2 CLI 연동 워크플로우', () => {
  
  test.beforeEach(async ({ page }) => {
    // 각 테스트 전에 홈페이지로 이동
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')
  })

  test('전체 v2 워크플로우 - Custom URL 호출까지', async ({ page }) => {
    console.log('🧪 v2 전체 워크플로우 테스트 시작')
    
    // 1. 웹페이지 접속 확인
    await expect(page).toHaveTitle(/TestscenarioMaker/i)
    console.log('✅ 1. 웹페이지 접속 성공')
    
    // 2. "테스트 시나리오 생성" 탭으로 이동 (이미 기본 탭이어야 함)
    const scenarioTab = page.locator('text=테스트 시나리오 생성')
    await expect(scenarioTab).toBeVisible({ timeout: 10000 })
    await scenarioTab.click()
    console.log('✅ 2. 시나리오 생성 탭 확인')
    
    // 3. Git 저장소 경로 입력
    const repoPathInput = page.locator('input[placeholder*="git/repository"]')
    await expect(repoPathInput).toBeVisible({ timeout: 5000 })
    await repoPathInput.fill(TEST_REPO_PATH)
    console.log('✅ 3. 저장소 경로 입력 완료')
    
    // 4. 생성하기 버튼 찾기 및 클릭 준비
    const generateButton = page.locator('button:has-text("테스트 시나리오 생성하기")')
    await expect(generateButton).toBeVisible({ timeout: 5000 })
    await expect(generateButton).toBeEnabled()
    console.log('✅ 4. 생성하기 버튼 확인')
    
    // 5. Custom URL Protocol 호출 모니터링 준비
    // 브라우저에서 URL 변경을 감지하기 위한 리스너 설정
    let customUrlCalled = false
    let customUrl = ''
    
    // page.on('request') 이벤트로는 custom protocol을 잡을 수 없으므로
    // window.location.href 변경을 감지하는 스크립트 주입
    await page.evaluate(() => {
      const originalLocationSetter = Object.getOwnPropertyDescriptor(window, 'location')?.set ||
                                    Object.getOwnPropertyDescriptor(window.location, 'href')?.set
      
      Object.defineProperty(window, 'customUrlCalled', {
        value: false,
        writable: true
      })
      
      Object.defineProperty(window, 'lastCustomUrl', {
        value: '',
        writable: true
      })
      
      // location.href 변경 감지
      const originalAssign = window.location.assign
      const originalReplace = window.location.replace
      
      window.location.assign = function(url: string) {
        if (url.startsWith('testscenariomaker://')) {
          ;(window as any).customUrlCalled = true
          ;(window as any).lastCustomUrl = url
          console.log('🔗 Custom URL 호출 감지:', url)
          return
        }
        return originalAssign.call(this, url)
      }
      
      // href 직접 설정 감지
      let originalHref = window.location.href
      Object.defineProperty(window.location, 'href', {
        get: () => originalHref,
        set: (url: string) => {
          if (url.startsWith('testscenariomaker://')) {
            ;(window as any).customUrlCalled = true
            ;(window as any).lastCustomUrl = url
            console.log('🔗 Custom URL href 설정 감지:', url)
            return
          }
          originalHref = url
        }
      })
    })
    
    // 6. CLI 대기 상태 UI 표시 확인 및 생성하기 버튼 클릭
    console.log('🖱️ 생성하기 버튼 클릭...')
    await generateButton.click()
    
    // 7. CLI 대기 상태 메시지 확인
    const cliWaitingMessage = page.locator('text=CLI 애플리케이션을 실행하고 있습니다')
    await expect(cliWaitingMessage).toBeVisible({ timeout: 3000 })
    console.log('✅ 5. CLI 대기 상태 UI 표시 확인')
    
    // 8. Custom URL 호출 확인 (JavaScript에서 감지)
    await page.waitForTimeout(2000) // Custom URL 호출 시간 대기
    
    const customUrlResult = await page.evaluate(() => ({
      called: (window as any).customUrlCalled,
      url: (window as any).lastCustomUrl
    }))
    
    expect(customUrlResult.called).toBe(true)
    expect(customUrlResult.url).toContain('testscenariomaker://generate')
    expect(customUrlResult.url).toContain('clientId=')
    expect(customUrlResult.url).toContain('repoPath=')
    console.log('✅ 6. Custom URL 호출 확인:', customUrlResult.url)
    
    console.log('🎉 v2 워크플로우 기본 흐름 테스트 완료!')
  })

  test('저장소 경로 유효성 검증', async ({ page }) => {
    console.log('🧪 저장소 경로 유효성 검증 테스트')
    
    // 시나리오 생성 탭으로 이동
    const scenarioTab = page.locator('text=테스트 시나리오 생성')
    await scenarioTab.click()
    
    // 잘못된 경로 입력
    const repoPathInput = page.locator('input[placeholder*="git/repository"]')
    await repoPathInput.fill('/nonexistent/path')
    
    const generateButton = page.locator('button:has-text("테스트 시나리오 생성하기")')
    await generateButton.click()
    
    // 오류 메시지 확인
    const errorMessage = page.locator('text=유효한 Git 저장소 경로를 입력해주세요')
    await expect(errorMessage).toBeVisible({ timeout: 5000 })
    console.log('✅ 잘못된 경로에 대한 오류 메시지 표시 확인')
    
    console.log('🎉 경로 유효성 검증 테스트 완료!')
  })

  test('빈 경로 입력 처리', async ({ page }) => {
    console.log('🧪 빈 경로 입력 처리 테스트')
    
    // 시나리오 생성 탭으로 이동
    const scenarioTab = page.locator('text=테스트 시나리오 생성')
    await scenarioTab.click()
    
    // 경로 입력 없이 생성하기 버튼 클릭
    const generateButton = page.locator('button:has-text("테스트 시나리오 생성하기")')
    await generateButton.click()
    
    // 오류 메시지 확인
    const errorMessage = page.locator('text=Git 저장소 경로를 입력해주세요')
    await expect(errorMessage).toBeVisible({ timeout: 5000 })
    console.log('✅ 빈 경로에 대한 오류 메시지 표시 확인')
    
    console.log('🎉 빈 경로 입력 처리 테스트 완료!')
  })

  test('RAG 시스템 패널 표시 확인', async ({ page }) => {
    console.log('🧪 RAG 시스템 패널 표시 테스트')
    
    // RAG 시스템 패널이 표시되는지 확인
    const ragPanel = page.locator('text=RAG 시스템')
    await expect(ragPanel).toBeVisible({ timeout: 10000 })
    console.log('✅ RAG 시스템 패널 표시 확인')
    
    console.log('🎉 RAG 시스템 패널 테스트 완료!')
  })

  test('설정 옵션 UI 확인', async ({ page }) => {
    console.log('🧪 설정 옵션 UI 테스트')
    
    // 시나리오 생성 탭으로 이동
    const scenarioTab = page.locator('text=테스트 시나리오 생성')
    await scenarioTab.click()
    
    // 성능 최적화 모드 체크박스 확인
    const performanceModeCheckbox = page.locator('text=성능 최적화 모드').locator('..')
    await expect(performanceModeCheckbox).toBeVisible()
    console.log('✅ 성능 최적화 모드 옵션 확인')
    
    // 입력 필드 확인
    const repoPathInput = page.locator('input[placeholder*="git/repository"]')
    await expect(repoPathInput).toBeVisible()
    console.log('✅ 저장소 경로 입력 필드 확인')
    
    console.log('🎉 설정 옵션 UI 테스트 완료!')
  })
})

test.describe('v2 백엔드 API 직접 테스트', () => {
  
  test('v2 API 엔드포인트 응답 확인', async ({ request }) => {
    console.log('🧪 v2 백엔드 API 직접 테스트')
    
    // 상태 조회 API 테스트
    const statusResponse = await request.get(`${BACKEND_URL}/api/v2/scenario/status/test_e2e_client`)
    expect(statusResponse.status()).toBe(200)
    
    const statusData = await statusResponse.json()
    expect(statusData.client_id).toBe('test_e2e_client')
    expect(statusData.is_generating).toBe(false)
    expect(statusData.status).toBe('idle')
    console.log('✅ v2 상태 조회 API 테스트 성공')
    
    // 헬스 체크 API 테스트
    const healthResponse = await request.get(`${BACKEND_URL}/api/health`)
    expect(healthResponse.status()).toBe(200)
    
    const healthData = await healthResponse.json()
    expect(healthData.status).toBe('healthy')
    console.log('✅ 헬스 체크 API 테스트 성공')
    
    console.log('🎉 v2 백엔드 API 테스트 완료!')
  })
})

test.describe('Custom URL Protocol 모킹 테스트', () => {
  
  test('Custom URL 생성 및 파싱 확인', async ({ page }) => {
    console.log('🧪 Custom URL 생성 및 파싱 테스트')
    
    // 브라우저에서 Custom URL 생성 로직 테스트
    const urlTestResult = await page.evaluate(() => {
      const clientId = 'test_client_url_' + Date.now()
      const repoPath = '/test/repo/path'
      const performanceMode = true
      
      // URL 생성 (실제 프론트엔드 로직과 동일)
      const customUrl = `testscenariomaker://generate?clientId=${clientId}&repoPath=${encodeURIComponent(repoPath)}&performanceMode=${performanceMode}`
      
      // URL 파싱 테스트
      const url = new URL(customUrl)
      const params = new URLSearchParams(url.search)
      
      return {
        originalUrl: customUrl,
        protocol: url.protocol,
        host: url.host,
        pathname: url.pathname,
        clientId: params.get('clientId'),
        repoPath: decodeURIComponent(params.get('repoPath') || ''),
        performanceMode: params.get('performanceMode') === 'true'
      }
    })
    
    // URL 형식 검증
    expect(urlTestResult.protocol).toBe('testscenariomaker:')
    expect(urlTestResult.pathname).toBe('/generate')
    expect(urlTestResult.clientId).toContain('test_client_url_')
    expect(urlTestResult.repoPath).toBe('/test/repo/path')
    expect(urlTestResult.performanceMode).toBe(true)
    
    console.log('✅ Custom URL 생성 및 파싱 확인:', urlTestResult.originalUrl)
    console.log('🎉 Custom URL 테스트 완료!')
  })
})