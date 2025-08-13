import { test, expect } from '@playwright/test'

/**
 * Streamlit vs React 앱 UI/UX 비교 테스트
 * 
 * 이 테스트는 기존 Streamlit 앱(app_streamlit_backup.py)과 
 * 새로운 React 앱의 기능을 비교합니다.
 */

test.describe('App Comparison Tests', () => {
  test.beforeEach(async ({ page }) => {
    // React 앱으로 이동
    await page.goto('/')
  })

  test('should display main page with correct title', async ({ page }) => {
    // 페이지 제목 확인
    await expect(page).toHaveTitle(/테스트 시나리오 자동 생성기/)
    
    // 헤더 확인
    await expect(page.locator('text=🤖 테스트 시나리오 자동 생성기')).toBeVisible()
  })

  test('should have two main tabs like Streamlit version', async ({ page }) => {
    // 탭이 존재하는지 확인
    await expect(page.locator('text=시나리오 생성')).toBeVisible()
    await expect(page.locator('text=피드백 분석')).toBeVisible()
    
    // 기본적으로 첫 번째 탭이 활성화되어 있는지 확인
    const scenarioTab = page.locator('[role="tab"]:has-text("시나리오 생성")')
    await expect(scenarioTab).toHaveAttribute('aria-selected', 'true')
  })

  test('should display RAG system information', async ({ page }) => {
    // RAG 시스템 섹션이 존재하는지 확인
    await expect(page.locator('text=RAG 시스템 정보')).toBeVisible()
    
    // RAG 시스템 섹션 펼치기
    await page.locator('text=RAG 시스템 정보').click()
    
    // RAG 관련 버튼들이 존재하는지 확인
    await expect(page.locator('text=문서 인덱싱')).toBeVisible()
    await expect(page.locator('text=전체 재인덱싱')).toBeVisible()
    await expect(page.locator('text=벡터 DB 초기화')).toBeVisible()
  })

  test('should have scenario generation form', async ({ page }) => {
    // Git 저장소 경로 입력 필드 확인
    const repoPathInput = page.locator('input[placeholder="/path/to/your/git/repository"]')
    await expect(repoPathInput).toBeVisible()
    
    // 성능 최적화 모드 체크박스 확인
    await expect(page.locator('text=성능 최적화 모드')).toBeVisible()
    
    // 생성 버튼 확인
    await expect(page.locator('text=테스트 시나리오 생성하기')).toBeVisible()
  })

  test('should validate repository path', async ({ page }) => {
    const repoPathInput = page.locator('input[placeholder="/path/to/your/git/repository"]')
    const generateButton = page.locator('text=테스트 시나리오 생성하기')
    
    // 빈 경로로 생성 시도
    await generateButton.click()
    
    // 오류 메시지가 표시되는지 확인
    await expect(page.locator('text=Git 저장소 경로를 입력해주세요')).toBeVisible()
    
    // 잘못된 경로 입력
    await repoPathInput.fill('/invalid/path')
    await generateButton.click()
    
    // 유효하지 않은 경로 오류 메시지 확인
    await expect(page.locator('text=유효한 Git 저장소 경로를 입력해주세요')).toBeVisible()
  })

  test('should switch between tabs correctly', async ({ page }) => {
    // 피드백 분석 탭 클릭
    await page.locator('text=피드백 분석').click()
    
    // 피드백 분석 탭이 활성화되었는지 확인
    const feedbackTab = page.locator('[role="tab"]:has-text("피드백 분석")')
    await expect(feedbackTab).toHaveAttribute('aria-selected', 'true')
    
    // 피드백 분석 내용이 표시되는지 확인
    await expect(page.locator('text=피드백 분석 대시보드')).toBeVisible()
    
    // 다시 시나리오 생성 탭으로 돌아가기
    await page.locator('text=시나리오 생성').click()
    
    // 시나리오 생성 탭이 활성화되었는지 확인
    const scenarioTab = page.locator('[role="tab"]:has-text("시나리오 생성")')
    await expect(scenarioTab).toHaveAttribute('aria-selected', 'true')
  })

  test('should display feedback analysis page when no feedback exists', async ({ page }) => {
    // 피드백 분석 탭으로 이동
    await page.locator('text=피드백 분석').click()
    
    // 피드백이 없을 때의 메시지 확인
    await expect(page.locator('text=아직 수집된 피드백이 없습니다')).toBeVisible()
  })

  test('should maintain responsive design', async ({ page }) => {
    // 데스크톱 크기에서 테스트
    await page.setViewportSize({ width: 1200, height: 800 })
    await expect(page.locator('text=🤖 테스트 시나리오 자동 생성기')).toBeVisible()
    
    // 태블릿 크기로 변경
    await page.setViewportSize({ width: 768, height: 1024 })
    await expect(page.locator('text=🤖 테스트 시나리오 자동 생성기')).toBeVisible()
    
    // 모바일 크기로 변경
    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('text=🤖 테스트 시나리오 자동 생성기')).toBeVisible()
  })

  test('should handle RAG system interactions', async ({ page }) => {
    // RAG 시스템 섹션 펼치기
    await page.locator('text=RAG 시스템 정보').click()
    
    // 문서 인덱싱 버튼 클릭 (모킹된 응답 기대)
    const indexButton = page.locator('text=문서 인덱싱')
    await expect(indexButton).toBeEnabled()
    
    // 벡터 DB 초기화 버튼도 확인
    const clearButton = page.locator('text=벡터 DB 초기화')
    await expect(clearButton).toBeEnabled()
  })

  test('should preserve session state during navigation', async ({ page }) => {
    // Git 저장소 경로 입력
    const repoPathInput = page.locator('input[placeholder="/path/to/your/git/repository"]')
    await repoPathInput.fill('/test/repository')
    
    // 피드백 분석 탭으로 이동
    await page.locator('text=피드백 분석').click()
    
    // 다시 시나리오 생성 탭으로 돌아가기
    await page.locator('text=시나리오 생성').click()
    
    // 입력한 경로가 유지되는지 확인
    await expect(repoPathInput).toHaveValue('/test/repository')
  })
})

test.describe('Performance Comparison', () => {
  test('should load faster than Streamlit equivalent', async ({ page }) => {
    const startTime = Date.now()
    
    // 페이지 로드
    await page.goto('/')
    
    // 주요 요소들이 로드될 때까지 대기
    await expect(page.locator('text=🤖 테스트 시나리오 자동 생성기')).toBeVisible()
    await expect(page.locator('text=시나리오 생성')).toBeVisible()
    await expect(page.locator('text=피드백 분석')).toBeVisible()
    
    const loadTime = Date.now() - startTime
    
    // React 앱은 3초 이내에 로드되어야 함 (Streamlit보다 빨라야 함)
    expect(loadTime).toBeLessThan(3000)
    
    console.log(`React 앱 로드 시간: ${loadTime}ms`)
  })

  test('should respond quickly to user interactions', async ({ page }) => {
    await page.goto('/')
    
    const startTime = Date.now()
    
    // 탭 전환 테스트
    await page.locator('text=피드백 분석').click()
    await expect(page.locator('text=피드백 분석 대시보드')).toBeVisible()
    
    const switchTime = Date.now() - startTime
    
    // 탭 전환은 500ms 이내에 완료되어야 함
    expect(switchTime).toBeLessThan(500)
    
    console.log(`탭 전환 시간: ${switchTime}ms`)
  })
})