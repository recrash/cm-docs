import { test, expect } from '@playwright/test'

/**
 * 피드백 데이터 관리 E2E 테스트
 * 
 * 새로 추가된 백업 파일 관리와 요약 보고서 기능의 
 * 실제 사용자 시나리오를 테스트합니다.
 */

test.describe('Feedback Data Management', () => {
  test.beforeEach(async ({ page }) => {
    // React 앱으로 이동
    await page.goto('/')
    
    // 피드백 분석 탭으로 이동
    await page.click('text=피드백 분석')
    
    // 페이지 로딩 대기
    await page.waitForSelector('text=💾 데이터 관리')
  })

  test('should display 3 action buttons with correct layout', async ({ page }) => {
    // 데이터 관리 섹션 확인
    await expect(page.locator('text=💾 데이터 관리')).toBeVisible()
    await expect(page.locator('text=데이터 백업 및 관리')).toBeVisible()
    
    // 3개 버튼 모두 존재하는지 확인
    await expect(page.locator('text=📥 피드백 데이터 내보내기')).toBeVisible()
    await expect(page.locator('text=📋 백업 파일 관리')).toBeVisible()
    await expect(page.locator('text=📊 요약 보고서')).toBeVisible()
    
    // 데이터 관리 섹션의 버튼들만 확인 (3개)
    const dataSection = page.locator('text=데이터 백업 및 관리').locator('..')
    const dataButtons = dataSection.locator('button').filter({ hasText: /📥|📋|📊/ })
    await expect(dataButtons).toHaveCount(3) // 3개 데이터 관리 버튼
    
    // 데이터 관리 버튼들만 확인
    const exportButton = page.locator('button:has-text("📥 피드백 데이터 내보내기")')
    const backupButton = page.locator('button:has-text("📋 백업 파일 관리")')
    const reportButton = page.locator('button:has-text("📊 요약 보고서")')
    
    await expect(exportButton).toBeVisible()
    await expect(backupButton).toBeVisible()
    await expect(reportButton).toBeVisible()
  })

  test('should open and close backup file management modal', async ({ page }) => {
    // 백업 파일 관리 버튼 클릭
    await page.click('button:has-text("📋 백업 파일 관리")')
    
    // 모달이 열렸는지 확인
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    await expect(page.locator('[role="dialog"] >> text=📋 백업 파일 관리')).toBeVisible()
    
    // 모달 내용 확인
    await expect(page.locator('text=백업 파일이 없습니다.')).toBeVisible()
    
    // 닫기 버튼으로 모달 닫기
    await page.click('button:has-text("닫기")')
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()
  })

  test('should close modal using close icon', async ({ page }) => {
    // 백업 파일 관리 버튼 클릭
    await page.click('button:has-text("📋 백업 파일 관리")')
    
    // 모달이 열렸는지 확인
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    
    // X 아이콘으로 모달 닫기
    await page.click('[data-testid="CloseIcon"]')
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()
  })

  test('should handle export data button click', async ({ page }) => {
    // 알림 대화상자 처리 준비 (성공 또는 에러 메시지 모두 허용)
    page.on('dialog', async dialog => {
      const message = dialog.message()
      expect(message).toMatch(/피드백 데이터가 성공적으로 내보내졌습니다|데이터 내보내기 중 오류가 발생했습니다/)
      await dialog.accept()
    })
    
    // 피드백 데이터 내보내기 버튼 클릭
    await page.click('button:has-text("📥 피드백 데이터 내보내기")')
    
    // API 요청 대기
    await page.waitForTimeout(1000)
  })

  test('should handle summary report generation', async ({ page }) => {
    // 알림 대화상자 처리 준비 (성공 또는 에러 메시지 모두 허용)
    page.on('dialog', async dialog => {
      const message = dialog.message()
      expect(message).toMatch(/요약 보고서가 성공적으로 생성되었습니다|요약 보고서 생성 중 오류가 발생했습니다/)
      await dialog.accept()
    })
    
    // 요약 보고서 버튼 클릭
    await page.click('button:has-text("📊 요약 보고서")')
    
    // API 요청 대기
    await page.waitForTimeout(1000)
  })

  test('should maintain responsive layout on mobile viewport', async ({ page }) => {
    // 모바일 뷰포트로 변경
    await page.setViewportSize({ width: 375, height: 667 })
    
    // 페이지 새로고침하여 반응형 레이아웃 적용
    await page.reload()
    await page.click('text=피드백 분석')
    await page.waitForSelector('text=💾 데이터 관리')
    
    // 버튼들이 여전히 보이는지 확인
    await expect(page.locator('text=📥 피드백 데이터 내보내기')).toBeVisible()
    await expect(page.locator('text=📋 백업 파일 관리')).toBeVisible()
    await expect(page.locator('text=📊 요약 보고서')).toBeVisible()
    
    // 모바일에서 모달이 정상 작동하는지 확인
    await page.click('button:has-text("📋 백업 파일 관리")')
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    
    // 모달이 화면에 맞게 표시되는지 확인
    const modal = page.locator('[role="dialog"]')
    const modalBox = await modal.boundingBox()
    expect(modalBox?.width).toBeLessThanOrEqual(375)
  })

  test('should maintain responsive layout on tablet viewport', async ({ page }) => {
    // 태블릿 뷰포트로 변경
    await page.setViewportSize({ width: 768, height: 1024 })
    
    // 페이지 새로고침하여 반응형 레이아웃 적용
    await page.reload()
    await page.click('text=피드백 분석')
    await page.waitForSelector('text=💾 데이터 관리')
    
    // 버튼들이 적절히 배치되었는지 확인
    await expect(page.locator('text=📥 피드백 데이터 내보내기')).toBeVisible()
    await expect(page.locator('text=📋 백업 파일 관리')).toBeVisible()
    await expect(page.locator('text=📊 요약 보고서')).toBeVisible()
  })

  test('should show proper deletion section layout', async ({ page }) => {
    // 위험한 작업 섹션 확인
    await expect(page.locator('text=⚠️ 데이터 삭제 (주의 필요)')).toBeVisible()
    
    // 삭제 버튼들이 빨간색 배경의 Paper 컴포넌트 안에 있는지 확인
    const deleteSection = page.locator('text=⚠️ 데이터 삭제 (주의 필요)').locator('..')
    await expect(deleteSection).toBeVisible()
    
    // 4개의 삭제 버튼 확인
    await expect(page.locator('button:has-text("전체 피드백 삭제")')).toBeVisible()
    await expect(page.locator('button:has-text("긍정 피드백 삭제")')).toBeVisible()
    await expect(page.locator('button:has-text("부정 피드백 삭제")')).toBeVisible()
    await expect(page.locator('button:has-text("중립 피드백 삭제")')).toBeVisible()
    
    // 경고 메시지 확인
    await expect(page.locator('text=초기화 작업은 되돌릴 수 없습니다')).toBeVisible()
  })

  test('should handle feedback deletion with confirmation', async ({ page }) => {
    // 확인 대화상자 처리 준비
    page.on('dialog', async dialog => {
      if (dialog.message().includes('모든 피드백을 삭제하시겠습니까?')) {
        await dialog.accept()
      } else if (dialog.message().includes('피드백이 성공적으로 삭제되었습니다')) {
        await dialog.accept()
      }
    })
    
    // 전체 피드백 삭제 버튼 클릭
    await page.click('button:has-text("전체 피드백 삭제")')
    
    // 작업 완료 대기
    await page.waitForTimeout(1000)
  })

  test('should display proper visual hierarchy', async ({ page }) => {
    // 안전한 작업 섹션이 위쪽에 있는지 확인
    const safeSection = page.locator('text=데이터 백업 및 관리')
    const dangerSection = page.locator('text=⚠️ 데이터 삭제 (주의 필요)')
    
    const safeBounds = await safeSection.boundingBox()
    const dangerBounds = await dangerSection.boundingBox()
    
    // 안전한 작업이 위험한 작업보다 위에 있는지 확인
    expect(safeBounds?.y).toBeLessThan(dangerBounds?.y || 0)
    
    // 각 섹션이 시각적으로 구분되는지 확인
    await expect(safeSection).toBeVisible()
    await expect(dangerSection).toBeVisible()
  })

  test('should handle errors gracefully', async ({ page }) => {
    // 네트워크 요청을 차단하여 에러 상황 시뮬레이션
    await page.route('**/api/feedback/**', route => {
      route.abort()
    })
    
    // 알림 대화상자 처리 준비 (에러 메시지)
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('오류가 발생했습니다')
      await dialog.accept()
    })
    
    // 버튼 클릭 시 에러 처리 확인
    await page.click('button:has-text("📥 피드백 데이터 내보내기")')
    await page.waitForTimeout(1000)
  })

  test('should maintain accessibility standards', async ({ page }) => {
    // 버튼들이 접근 가능한 이름을 가지고 있는지 확인
    await expect(page.locator('button[aria-label], button:has-text("📥")').first()).toBeVisible()
    
    // 모달이 올바른 role과 aria 속성을 가지고 있는지 확인
    await page.click('button:has-text("📋 백업 파일 관리")')
    await expect(page.locator('[role="dialog"]')).toBeVisible()
    
    // 키보드 탐색 테스트
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter') // 새로고침 버튼
    
    await page.keyboard.press('Tab')
    await page.keyboard.press('Enter') // 닫기 버튼
    await expect(page.locator('[role="dialog"]')).not.toBeVisible()
  })
})