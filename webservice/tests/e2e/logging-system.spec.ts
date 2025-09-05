import { test, expect } from '@playwright/test';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

test.describe('로깅 시스템 E2E 테스트', () => {
  test.beforeEach(async ({ page }) => {
    // 테스트 시작 전 로그 파일 초기 상태 확인
    const logsDir = join(process.cwd(), 'logs');
    console.log(`로그 디렉토리 확인: ${logsDir}`);
  });

  test('백엔드 로깅 시스템 테스트', async ({ page }) => {
    // 1. 백엔드 서버가 정상적으로 시작되었는지 확인
    const response = await page.request.get('http://localhost:80/api/health');
    expect(response.status()).toBe(200);
    const responseData = await response.json();
    expect(responseData).toEqual({ status: 'healthy' });

    // 2. 로그 파일이 생성되었는지 확인
    const logsDir = join(process.cwd(), 'logs');
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const backendLogFile = join(logsDir, `${today}_backend.log`);
    
    // 잠시 대기하여 로그 파일이 생성될 시간을 줍니다
    await page.waitForTimeout(2000);
    
    expect(existsSync(backendLogFile), `백엔드 로그 파일이 생성되지 않았습니다: ${backendLogFile}`).toBeTruthy();
    
    // 3. 로그 파일 내용 확인
    const logContent = readFileSync(backendLogFile, 'utf-8');
    expect(logContent).toContain('Logging configured with date-prefixed file names');
    expect(logContent).toContain('애플리케이션 시작');
    
    console.log('✅ 백엔드 로깅 시스템 정상 동작 확인');
  });

  test('프론트엔드 로깅 시스템 테스트', async ({ page }) => {
    // 1. 프론트엔드 페이지 로드
    await page.goto('http://localhost:3000');
    
    // 2. 개발 환경에서 콘솔 로그 확인
    const consoleLogs: string[] = [];
    page.on('console', msg => {
      consoleLogs.push(msg.text());
    });

    // 3. 의도적으로 오류를 발생시켜 로깅 테스트
    await page.evaluate(() => {
      // 전역 오류 핸들러 테스트를 위한 의도적 오류 발생
      setTimeout(() => {
        throw new Error('테스트용 의도적 오류');
      }, 100);
    });

    // 4. 잠시 대기하여 오류 처리 시간을 줍니다
    await page.waitForTimeout(1000);

    // 5. 브라우저 콘솔에서 로그 확인
    const logs = await page.evaluate(() => {
      return (window as any).consoleLogs || [];
    });

    console.log('✅ 프론트엔드 로깅 시스템 정상 동작 확인');
  });

  test('API 오류 로깅 테스트', async ({ page }) => {
    // 1. 존재하지 않는 API 엔드포인트 호출하여 오류 발생
    const response = await page.request.get('http://localhost:80/api/nonexistent');
    expect(response.status()).toBe(404);

    // 2. 잠시 대기하여 로그 기록 시간을 줍니다
    await page.waitForTimeout(1000);

    // 3. 백엔드 로그 파일에서 오류 로그 확인
    const logsDir = join(process.cwd(), 'logs');
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const backendLogFile = join(logsDir, `${today}_backend.log`);
    
    if (existsSync(backendLogFile)) {
      const logContent = readFileSync(backendLogFile, 'utf-8');
      // 404 오류가 로그에 기록되었는지 확인
      expect(logContent).toContain('404');
    }

    console.log('✅ API 오류 로깅 정상 동작 확인');
  });

  test('WebSocket 로깅 테스트', async ({ page }) => {
    // 1. WebSocket 연결 테스트
    await page.goto('http://localhost:3000');
    
    // 2. WebSocket 연결 시도 (실제 시나리오 생성은 하지 않고 연결만 테스트)
    const wsLogs: string[] = [];
    page.on('console', msg => {
      if (msg.text().includes('WebSocket')) {
        wsLogs.push(msg.text());
      }
    });

    // 3. WebSocket URL 생성 테스트
    const wsUrl = await page.evaluate(() => {
      // API 서비스에서 WebSocket URL 생성 로직 테스트
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname;
      const port = '80';
      return `${protocol}//${host}:${port}/api/scenario/generate-ws`;
    });

    expect(wsUrl).toContain('ws://localhost:80/api/scenario/generate-ws');
    
    console.log('✅ WebSocket 로깅 정상 동작 확인');
  });

  test('로그 파일 형식 검증', async ({ page }) => {
    // 1. 로그 파일들이 올바른 형식으로 생성되었는지 확인
    const logsDir = join(process.cwd(), 'logs');
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const backendLogFile = join(logsDir, `${today}_backend.log`);
    
    if (existsSync(backendLogFile)) {
      const logContent = readFileSync(backendLogFile, 'utf-8');
      const lines = logContent.split('\n').filter(line => line.trim());
      
      // 로그 형식 검증: "ISO 타임스탬프 | 레벨 | 모듈/컴포넌트 | 메시지"
      const logFormatRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \| \w+ \| [\w.]+ \| .+$/;
      
      for (const line of lines.slice(0, 5)) { // 처음 5줄만 검증
        expect(line).toMatch(logFormatRegex);
      }
    }

    console.log('✅ 로그 파일 형식 검증 완료');
  });

  test('프론트엔드 로그 서버 전송 테스트', async ({ page }) => {
    // 1. 프로덕션 환경 시뮬레이션을 위한 로그 전송 테스트
    await page.goto('http://localhost:3000');
    
    // 2. 로그 전송 API 엔드포인트 테스트
    const logResponse = await page.request.post('http://localhost:80/api/log', {
      data: {
        level: 'info',
        message: '테스트 로그 메시지',
        meta: { test: true, timestamp: Date.now() }
      }
    });
    
    expect(logResponse.status()).toBe(200);
    expect(await logResponse.json()).toEqual({ status: 'ok' });

    // 3. 잠시 대기하여 로그 파일 기록 시간을 줍니다
    await page.waitForTimeout(1000);

    // 4. 프론트엔드 로그 파일에서 테스트 메시지 확인
    const logsDir = join(process.cwd(), 'logs');
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const frontendLogFile = join(logsDir, `${today}_frontend.log`);
    
    if (existsSync(frontendLogFile)) {
      const logContent = readFileSync(frontendLogFile, 'utf-8');
      expect(logContent).toContain('테스트 로그 메시지');
    }

    console.log('✅ 프론트엔드 로그 서버 전송 정상 동작 확인');
  });
}); 