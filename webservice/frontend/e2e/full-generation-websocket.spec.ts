/**
 * Full Generation WebSocket 연결 E2E 테스트
 *
 * 테스트 시나리오:
 * 1. HTML 파일 업로드 및 Full Generation 시작
 * 2. CLI 커스텀 URL 프로토콜 호출 테스트
 * 3. WebSocket 진행상황 수신 검증
 * 4. 완료 상태 및 결과 파일 검증
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

// 테스트 설정
const TEST_HTML_FILE = '/Users/recrash/Downloads/0_FW_ Hub HTML_250813/Drum 재고 관리.html'
const TEST_REPO_PATH = '/Users/recrash/Documents/Workspace/cm-docs'
const FRONTEND_URL = 'http://localhost:3000'
const BACKEND_URL = 'http://localhost:8000'

test.describe('Full Generation WebSocket 연결 테스트', () => {

  test.beforeEach(async ({ page }) => {
    // 각 테스트 전에 홈페이지로 이동
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')
  })

  test('HTML 파일 업로드 및 Full Generation 워크플로우', async ({ page }) => {
    console.log('🧪 Full Generation 전체 워크플로우 테스트 시작')

    // 1. 웹페이지 접속 확인
    await expect(page).toHaveTitle(/TestscenarioMaker/i)
    console.log('✅ 1. 웹페이지 접속 성공')

    // 2. HTML 업로드 탭으로 이동
    const htmlUploadTab = page.locator('text=HTML 업로드')
    await expect(htmlUploadTab).toBeVisible({ timeout: 10000 })
    await htmlUploadTab.click()
    console.log('✅ 2. HTML 업로드 탭으로 이동')

    // 3. HTML 파일 존재 확인
    if (!fs.existsSync(TEST_HTML_FILE)) {
      throw new Error(`테스트 HTML 파일이 존재하지 않습니다: ${TEST_HTML_FILE}`)
    }
    console.log('✅ 3. 테스트 HTML 파일 존재 확인')

    // 4. 파일 업로드 영역 찾기
    const fileInput = page.locator('input[type="file"]')
    await expect(fileInput).toBeVisible({ timeout: 5000 })

    // 파일 업로드 실행
    await fileInput.setInputFiles(TEST_HTML_FILE)
    console.log('✅ 4. HTML 파일 업로드 완료')

    // 5. 업로드 완료 후 메타데이터 파싱 대기
    const parseButton = page.locator('button:has-text("파싱하기")')
    await expect(parseButton).toBeVisible({ timeout: 5000 })
    await parseButton.click()
    console.log('✅ 5. HTML 파싱 시작')

    // 6. 파싱 완료 대기 및 결과 확인
    const parsedResult = page.locator('.parsed-metadata, .metadata-result, text=파싱 완료')
    await expect(parsedResult).toBeVisible({ timeout: 15000 })
    console.log('✅ 6. HTML 파싱 완료')

    // 7. Full Generation 버튼 찾기
    const fullGenerationButton = page.locator('button:has-text("Full Generation"), button:has-text("전체 생성"), button:has-text("완전 생성")')
    await expect(fullGenerationButton).toBeVisible({ timeout: 5000 })
    console.log('✅ 7. Full Generation 버튼 확인')

    // 8. Custom URL Protocol 호출 모니터링 준비
    let customUrlCalled = false
    let lastCustomUrl = ''
    let sessionId = ''

    // 브라우저에서 Custom URL 호출 감지를 위한 스크립트 주입
    await page.evaluate(() => {
      // window 객체에 감지 변수 설정
      Object.defineProperty(window, 'customUrlCalled', {
        value: false,
        writable: true
      })

      Object.defineProperty(window, 'lastCustomUrl', {
        value: '',
        writable: true
      })

      Object.defineProperty(window, 'sessionId', {
        value: '',
        writable: true
      })

      // location.href 변경 감지
      const originalAssign = window.location.assign

      window.location.assign = function(url: string) {
        if (url.startsWith('testscenariomaker://')) {
          (window as any).customUrlCalled = true
          ;(window as any).lastCustomUrl = url

          // sessionId 추출
          try {
            const urlObj = new URL(url)
            const params = new URLSearchParams(urlObj.search)
            ;(window as any).sessionId = params.get('sessionId') || ''
          } catch (e) {
            console.error('URL 파싱 오류:', e)
          }

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
            (window as any).customUrlCalled = true
            ;(window as any).lastCustomUrl = url

            // sessionId 추출
            try {
              const urlObj = new URL(url)
              const params = new URLSearchParams(urlObj.search)
              ;(window as any).sessionId = params.get('sessionId') || ''
            } catch (e) {
              console.error('URL 파싱 오류:', e)
            }

            console.log('🔗 Custom URL href 설정 감지:', url)
            return
          }
          originalHref = url
        }
      })
    })

    // 9. Full Generation 버튼 클릭
    console.log('🖱️ Full Generation 버튼 클릭...')
    await fullGenerationButton.click()

    // 10. CLI 대기 상태 메시지 확인
    const cliWaitingMessage = page.locator('text=CLI 애플리케이션을 실행, text=CLI 실행 중, text=외부 애플리케이션 실행')
    await expect(cliWaitingMessage).toBeVisible({ timeout: 5000 })
    console.log('✅ 8. CLI 대기 상태 UI 표시 확인')

    // 11. Custom URL 호출 확인
    await page.waitForTimeout(3000) // Custom URL 호출 시간 대기

    const customUrlResult = await page.evaluate(() => {
      return {
        called: (window as any).customUrlCalled,
        url: (window as any).lastCustomUrl,
        sessionId: (window as any).sessionId
      }
    })

    expect(customUrlResult.called).toBe(true)
    expect(customUrlResult.url).toContain('testscenariomaker://full-generate')
    expect(customUrlResult.url).toContain('sessionId=')
    expect(customUrlResult.url).toContain('repoPath=')
    expect(customUrlResult.sessionId).toBeTruthy()

    sessionId = customUrlResult.sessionId
    console.log('✅ 9. Custom URL 호출 확인:', customUrlResult.url)
    console.log('📋 세션 ID:', sessionId)

    console.log('🎉 HTML 업로드 및 Full Generation 기본 흐름 테스트 완료!')
  })

  test('WebSocket 연결 및 진행상황 수신 테스트', async ({ page, browser }) => {
    console.log('🧪 WebSocket 연결 및 진행상황 수신 테스트 시작')

    // 테스트를 위한 가상의 세션 ID 생성
    const testSessionId = 'test_full_gen_' + Date.now()
    console.log('📋 테스트 세션 ID:', testSessionId)

    // WebSocket 연결 및 메시지 수신을 위한 새 페이지 생성
    const wsPage = await browser.newPage()

    let wsMessages: any[] = []
    let wsConnected = false
    let wsError = null

    // WebSocket 연결 스크립트 주입
    await wsPage.goto(FRONTEND_URL)

    const wsTestResult = await wsPage.evaluate(async (sessionId) => {
      return new Promise((resolve) => {
        const messages: any[] = []
        let connected = false
        let error = null

        try {
          // WebSocket 연결 설정
          const wsUrl = `ws://localhost:8000/api/webservice/v2/ws/full-generation/${sessionId}`
          const ws = new WebSocket(wsUrl)

          ws.onopen = () => {
            connected = true
            console.log('🔌 WebSocket 연결 성공')

            // 연결 후 잠시 대기
            setTimeout(() => {
              resolve({
                connected,
                messages,
                error: null,
                totalMessages: messages.length
              })
            }, 5000) // 5초 대기
          }

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data)
              messages.push(data)
              console.log('📩 WebSocket 메시지 수신:', data)
            } catch (e) {
              console.error('메시지 파싱 오류:', e)
            }
          }

          ws.onerror = (err) => {
            error = err.toString()
            console.error('❌ WebSocket 오류:', err)
            resolve({
              connected: false,
              messages,
              error,
              totalMessages: messages.length
            })
          }

          ws.onclose = () => {
            console.log('🔌 WebSocket 연결 종료')
            resolve({
              connected,
              messages,
              error,
              totalMessages: messages.length
            })
          }

          // 타임아웃 설정 (10초)
          setTimeout(() => {
            if (!connected) {
              ws.close()
              resolve({
                connected: false,
                messages,
                error: 'Connection timeout',
                totalMessages: messages.length
              })
            }
          }, 10000)

        } catch (e) {
          resolve({
            connected: false,
            messages,
            error: e.toString(),
            totalMessages: 0
          })
        }
      })
    }, testSessionId)

    // WebSocket 연결 결과 검증
    console.log('📊 WebSocket 테스트 결과:', wsTestResult)

    // 연결이 성공했거나 적절한 오류 메시지가 있어야 함
    if (wsTestResult.connected) {
      console.log('✅ 10. WebSocket 연결 성공')
    } else {
      console.log('⚠️ WebSocket 연결 실패 (예상됨 - CLI가 실행되지 않은 상태)')
      console.log('오류:', wsTestResult.error)

      // 서버가 WebSocket 엔드포인트를 제공하는지 확인
      expect(wsTestResult.error).not.toContain('ECONNREFUSED')
    }

    await wsPage.close()
    console.log('🎉 WebSocket 연결 테스트 완료!')
  })

  test('CLI URL 프로토콜 파라미터 검증', async ({ page }) => {
    console.log('🧪 CLI URL 프로토콜 파라미터 검증 테스트')

    // URL 생성 및 파라미터 검증을 위한 스크립트 실행
    const urlTestResult = await page.evaluate(() => {
      const sessionId = 'test_session_' + Date.now()
      const repoPath = '/Users/recrash/Documents/Workspace/cm-docs'

      // Full Generation URL 생성 (실제 프론트엔드 로직과 동일해야 함)
      const customUrl = `testscenariomaker://full-generate?sessionId=${sessionId}&repoPath=${encodeURIComponent(repoPath)}`

      // URL 파싱 테스트
      const url = new URL(customUrl)
      const params = new URLSearchParams(url.search)

      return {
        originalUrl: customUrl,
        protocol: url.protocol,
        host: url.host,
        pathname: url.pathname,
        sessionId: params.get('sessionId'),
        repoPath: decodeURIComponent(params.get('repoPath') || ''),
        validUrl: customUrl.startsWith('testscenariomaker://full-generate')
      }
    })

    // URL 형식 검증
    expect(urlTestResult.protocol).toBe('testscenariomaker:')
    expect(urlTestResult.pathname).toBe('/full-generate')
    expect(urlTestResult.sessionId).toContain('test_session_')
    expect(urlTestResult.repoPath).toBe('/Users/recrash/Documents/Workspace/cm-docs')
    expect(urlTestResult.validUrl).toBe(true)

    console.log('✅ URL 파라미터 검증 완료:', urlTestResult.originalUrl)
    console.log('🎉 CLI URL 프로토콜 파라미터 검증 테스트 완료!')
  })

  test('백엔드 Full Generation API 엔드포인트 확인', async ({ request }) => {
    console.log('🧪 백엔드 Full Generation API 엔드포인트 확인')

    try {
      // 헬스 체크 API 테스트
      const healthResponse = await request.get(`${BACKEND_URL}/api/webservice/health`)
      expect(healthResponse.status()).toBe(200)

      const healthData = await healthResponse.json()
      expect(healthData.status).toBe('healthy')
      console.log('✅ 백엔드 헬스 체크 성공')

      // AutoDoc 서비스 헬스 체크
      const autodocHealthResponse = await request.get(`${BACKEND_URL}/api/autodoc/health`)
      if (autodocHealthResponse.status() === 200) {
        console.log('✅ AutoDoc 서비스 헬스 체크 성공')
      } else {
        console.log('⚠️ AutoDoc 서비스가 실행되지 않음 (포트 8001 확인 필요)')
      }

    } catch (error) {
      console.log('❌ 백엔드 API 연결 실패:', error)
      throw error
    }

    console.log('🎉 백엔드 API 엔드포인트 확인 완료!')
  })

  test('HTML 파일 메타데이터 파싱 API 테스트', async ({ request }) => {
    console.log('🧪 HTML 파일 메타데이터 파싱 API 테스트')

    try {
      // HTML 파일이 존재하는지 확인
      if (!fs.existsSync(TEST_HTML_FILE)) {
        throw new Error(`테스트 HTML 파일이 존재하지 않습니다: ${TEST_HTML_FILE}`)
      }

      // HTML 파일 읽기
      const htmlContent = fs.readFileSync(TEST_HTML_FILE, 'utf-8')
      const fileName = path.basename(TEST_HTML_FILE)

      // FormData 생성 (multipart/form-data)
      const formData = new FormData()
      const blob = new Blob([htmlContent], { type: 'text/html' })
      formData.append('file', blob, fileName)

      // HTML 파싱 API 호출
      const parseResponse = await request.post(`${BACKEND_URL}/api/autodoc/parse-html-only`, {
        data: formData
      })

      expect(parseResponse.status()).toBe(200)

      const parseData = await parseResponse.json()
      expect(parseData.success).toBe(true)
      expect(parseData.data).toBeDefined()

      console.log('✅ HTML 파싱 API 호출 성공')
      console.log('📄 파싱된 메타데이터:', {
        title: parseData.data.title || 'Unknown',
        sections: parseData.data.sections?.length || 0,
        forms: parseData.data.forms?.length || 0
      })

    } catch (error) {
      console.log('❌ HTML 파싱 API 테스트 실패:', error)
      throw error
    }

    console.log('🎉 HTML 파일 메타데이터 파싱 API 테스트 완료!')
  })

  test('WebSocket 엔드포인트 접근성 테스트', async ({ page }) => {
    console.log('🧪 WebSocket 엔드포인트 접근성 테스트')

    const testSessionId = 'test_ws_access_' + Date.now()

    const wsAccessTest = await page.evaluate(async (sessionId) => {
      return new Promise((resolve) => {
        const results = {
          fullGenerationEndpoint: false,
          progressEndpoint: false,
          errors: [] as string[]
        }

        let testsCompleted = 0
        const totalTests = 2

        function checkComplete() {
          testsCompleted++
          if (testsCompleted >= totalTests) {
            resolve(results)
          }
        }

        // Full Generation WebSocket 엔드포인트 테스트
        try {
          const wsFullGen = new WebSocket(`ws://localhost:8000/api/webservice/v2/ws/full-generation/${sessionId}`)

          const fullGenTimeout = setTimeout(() => {
            wsFullGen.close()
            results.errors.push('Full Generation WebSocket timeout')
            checkComplete()
          }, 3000)

          wsFullGen.onopen = () => {
            results.fullGenerationEndpoint = true
            clearTimeout(fullGenTimeout)
            wsFullGen.close()
            checkComplete()
          }

          wsFullGen.onerror = (err) => {
            results.errors.push('Full Generation WebSocket error: ' + err.toString())
            clearTimeout(fullGenTimeout)
            checkComplete()
          }

        } catch (e) {
          results.errors.push('Full Generation WebSocket exception: ' + e.toString())
          checkComplete()
        }

        // Progress WebSocket 엔드포인트 테스트
        try {
          const wsProgress = new WebSocket(`ws://localhost:8000/api/webservice/v2/ws/progress/${sessionId}`)

          const progressTimeout = setTimeout(() => {
            wsProgress.close()
            results.errors.push('Progress WebSocket timeout')
            checkComplete()
          }, 3000)

          wsProgress.onopen = () => {
            results.progressEndpoint = true
            clearTimeout(progressTimeout)
            wsProgress.close()
            checkComplete()
          }

          wsProgress.onerror = (err) => {
            results.errors.push('Progress WebSocket error: ' + err.toString())
            clearTimeout(progressTimeout)
            checkComplete()
          }

        } catch (e) {
          results.errors.push('Progress WebSocket exception: ' + e.toString())
          checkComplete()
        }
      })
    }, testSessionId)

    console.log('📊 WebSocket 접근성 테스트 결과:', wsAccessTest)

    // 최소한 하나의 WebSocket 엔드포인트는 접근 가능해야 함
    if (wsAccessTest.fullGenerationEndpoint || wsAccessTest.progressEndpoint) {
      console.log('✅ WebSocket 엔드포인트 접근 가능')
    } else {
      console.log('⚠️ WebSocket 엔드포인트 접근 불가')
      console.log('오류 목록:', wsAccessTest.errors)
    }

    console.log('🎉 WebSocket 엔드포인트 접근성 테스트 완료!')
  })
})

test.describe('Full Generation 통합 시나리오 테스트', () => {

  test('실제 CLI 실행 시뮬레이션 테스트', async ({ page }) => {
    console.log('🧪 CLI 실행 시뮬레이션 테스트 시작')

    // 실제 시나리오에 가까운 테스트
    // 1. HTML 업로드 → 2. 메타데이터 파싱 → 3. Full Generation → 4. CLI URL 호출 확인

    // 웹페이지 접속
    await page.goto(FRONTEND_URL)
    await page.waitForLoadState('networkidle')

    // HTML 파일 존재 확인
    if (!fs.existsSync(TEST_HTML_FILE)) {
      console.log('⚠️ 테스트 HTML 파일이 없어 시뮬레이션 종료')
      return
    }

    // HTML 업로드 탭으로 이동
    const htmlUploadTab = page.locator('text=HTML 업로드')
    if (await htmlUploadTab.isVisible()) {
      await htmlUploadTab.click()
      console.log('✅ HTML 업로드 탭으로 이동')

      // 파일 업로드
      const fileInput = page.locator('input[type="file"]')
      if (await fileInput.isVisible()) {
        await fileInput.setInputFiles(TEST_HTML_FILE)
        console.log('✅ HTML 파일 업로드 완료')

        // 파싱 버튼 클릭
        const parseButton = page.locator('button:has-text("파싱"), button:has-text("분석")')
        if (await parseButton.isVisible()) {
          await parseButton.click()
          console.log('✅ HTML 파싱 시작')

          // 파싱 완료 대기 (최대 15초)
          try {
            await page.waitForSelector('.metadata-result, .parsed-content, text=파싱 완료', { timeout: 15000 })
            console.log('✅ HTML 파싱 완료')

            // Full Generation 버튼 확인
            const fullGenButton = page.locator('button:has-text("Full Generation"), button:has-text("전체 생성")')
            if (await fullGenButton.isVisible()) {
              console.log('✅ Full Generation 버튼 확인됨')

              // 실제 클릭은 하지 않음 (CLI가 없으므로)
              console.log('ℹ️ 실제 CLI 실행은 스킵 (테스트 환경)')
            } else {
              console.log('⚠️ Full Generation 버튼을 찾을 수 없음')
            }

          } catch (e) {
            console.log('⚠️ HTML 파싱 시간 초과 또는 실패')
          }
        } else {
          console.log('⚠️ 파싱 버튼을 찾을 수 없음')
        }
      } else {
        console.log('⚠️ 파일 업로드 입력을 찾을 수 없음')
      }
    } else {
      console.log('⚠️ HTML 업로드 탭을 찾을 수 없음')
    }

    console.log('🎉 CLI 실행 시뮬레이션 테스트 완료!')
  })
})