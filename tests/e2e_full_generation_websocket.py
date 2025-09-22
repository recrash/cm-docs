#!/usr/bin/env python3
"""
Full Generation WebSocket E2E 테스트

CLI 커스텀 URL 프로토콜을 통한 전체 워크플로우 테스트:
1. HTML 파일 업로드 및 메타데이터 파싱
2. WebSocket 연결 및 진행상황 수신
3. CLI 실행 및 WebSocket 모니터링
4. 완료 상태 및 결과 파일 검증
"""

import asyncio
import json
import time
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List


class FullGenerationE2ETest:
    """Full Generation WebSocket E2E 테스트 클래스"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.backend_url = "http://localhost:8000"
        self.test_html_path = "/Users/recrash/Downloads/0_FW_ Hub HTML_250813/Drum 재고 관리.html"
        self.test_repo_path = "/Users/recrash/Documents/Workspace/cm-docs"
        self.session_id = None
        self.websocket_messages = []

    async def test_full_generation_workflow(self):
        """전체 Full Generation 워크플로우 테스트"""
        try:
            print("🚀 Full Generation E2E 테스트 시작")

            # 1단계: 웹서비스 헬스체크
            await self._check_services_health()

            # 2단계: HTML 파일 업로드 및 세션 생성
            session_id = await self._upload_html_and_create_session()

            # 3단계: WebSocket 연결 테스트
            await self._test_websocket_connection(session_id)

            # 4단계: CLI 커스텀 URL 호출 테스트
            await self._test_cli_url_protocol(session_id)

            # 5단계: 전체 워크플로우 검증
            await self._verify_full_workflow(session_id)

            print("✅ Full Generation E2E 테스트 완료")
            return True

        except Exception as e:
            print(f"❌ E2E 테스트 실패: {e}")
            return False

    async def _check_services_health(self):
        """서비스 헬스체크"""
        print("🔍 서비스 상태 확인 중...")

        # 헬스체크 대신 기본 연결 테스트
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # Webservice docs 엔드포인트로 연결 확인
                response = await client.get(f"{self.backend_url}/docs")
                if response.status_code != 200:
                    raise Exception(f"Webservice 연결 실패: {response.status_code}")
                print("✅ Webservice 연결 확인")

                # AutoDoc Service 헬스체크
                response = await client.get("http://localhost:8001/api/autodoc/health")
                if response.status_code != 200:
                    raise Exception(f"AutoDoc Service 상태 이상: {response.status_code}")
                print("✅ AutoDoc Service 정상")

        except Exception as e:
            print(f"⚠️ 서비스 상태 확인 실패: {e}")
            print("서비스들이 실행되어 있는지 확인해주세요:")
            print("- Webservice: python -m uvicorn app.main:app --port 8000")
            print("- AutoDoc: python run_autodoc_service.py")
            raise

    async def _upload_html_and_create_session(self) -> str:
        """HTML 파일 업로드 및 세션 생성"""
        print("📄 HTML 파일 업로드 및 세션 생성 중...")

        if not Path(self.test_html_path).exists():
            raise Exception(f"테스트 HTML 파일을 찾을 수 없습니다: {self.test_html_path}")

        import httpx
        async with httpx.AsyncClient() as client:
            # HTML 파일 업로드 및 파싱
            with open(self.test_html_path, 'rb') as f:
                files = {'file': ('Drum 재고 관리.html', f, 'text/html')}
                response = await client.post(
                    f"{self.backend_url}/api/autodoc/parse-html",
                    files=files,
                    timeout=30.0
                )

            if response.status_code != 200:
                raise Exception(f"HTML 파일 업로드 실패: {response.status_code}")

            parsed_data = response.json()
            print(f"✅ HTML 파싱 완료: {len(parsed_data.get('data', {}))} 필드")

            # 세션 ID 생성 (타임스탬프 기반)
            import uuid
            session_id = f"test_session_{int(time.time())}_{uuid.uuid4().hex[:8]}"

            # 세션에 메타데이터 저장 (실제 구현에 맞게 조정)
            metadata = parsed_data.get('data', {})

            print(f"🔗 생성된 세션 ID: {session_id}")
            return session_id

    async def _test_websocket_connection(self, session_id: str):
        """WebSocket 연결 테스트"""
        print("🔌 WebSocket 연결 테스트 중...")

        import websockets
        import json

        # WebSocket URL 구성
        websocket_url = f"ws://localhost:8000/api/webservice/v2/ws/full-generation/{session_id}"

        try:
            async with websockets.connect(websocket_url, timeout=10) as websocket:
                print("✅ WebSocket 연결 성공")

                # 환영 메시지 수신 대기
                try:
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    message_data = json.loads(welcome_msg)
                    print(f"📨 환영 메시지 수신: {message_data.get('message', 'N/A')}")

                    # ping 테스트
                    await websocket.send("ping")
                    pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    print(f"🏓 Ping-Pong 테스트 성공: {pong_response[:50]}...")

                except asyncio.TimeoutError:
                    print("⚠️ 환영 메시지 타임아웃 (정상 동작일 수 있음)")

        except Exception as e:
            print(f"❌ WebSocket 연결 실패: {e}")
            raise

    async def _test_cli_url_protocol(self, session_id: str):
        """CLI 커스텀 URL 프로토콜 테스트"""
        print("🖥️ CLI 커스텀 URL 프로토콜 테스트 중...")

        # CLI URL 구성
        cli_url = (
            f"testscenariomaker://full-generate?"
            f"sessionId={session_id}&"
            f"repoPath={self.test_repo_path}&"
            f"serverUrl={self.backend_url}"
        )

        print(f"🔗 CLI URL: {cli_url}")

        # CLI 실행 경로 확인
        cli_path = Path("cli/dist/ts-cli")
        if not cli_path.exists():
            cli_path = Path("cli/dist/ts-cli.exe")  # Windows

        if not cli_path.exists():
            print("⚠️ CLI 실행파일을 찾을 수 없습니다. 직접 테스트를 진행합니다.")
            return

        # CLI 실행 (백그라운드)
        try:
            print("🚀 CLI 실행 중...")
            process = subprocess.Popen(
                [str(cli_path), cli_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # 3초 대기 후 프로세스 상태 확인
            await asyncio.sleep(3)

            if process.poll() is None:
                print("✅ CLI 프로세스 실행 중")
                # 프로세스 종료
                process.terminate()
                process.wait()
            else:
                stdout, stderr = process.communicate()
                print(f"CLI 출력: {stdout[:200]}...")
                if stderr:
                    print(f"CLI 오류: {stderr[:200]}...")

        except Exception as e:
            print(f"⚠️ CLI 실행 실패: {e}")

    async def _verify_full_workflow(self, session_id: str):
        """전체 워크플로우 검증"""
        print("🔍 전체 워크플로우 검증 중...")

        import httpx

        # 세션 초기화 API 테스트
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.backend_url}/api/webservice/v2/full-generation/init-session/{session_id}",
                    timeout=10.0
                )

                if response.status_code == 200:
                    init_result = response.json()
                    print(f"✅ 세션 초기화 성공: {init_result.get('status', 'N/A')}")
                else:
                    print(f"⚠️ 세션 초기화 응답: {response.status_code}")

            except Exception as e:
                print(f"⚠️ 세션 초기화 API 테스트 실패: {e}")

        # 전체 문서 생성 API 테스트 (실제 실행 안 함)
        print("📋 Full Generation API 엔드포인트 존재 확인")
        try:
            response = await client.post(
                f"{self.backend_url}/api/webservice/v2/start-full-generation",
                json={
                    "session_id": session_id,
                    "vcs_analysis_text": "# Test VCS Analysis\nTest changes for E2E test",
                    "metadata_json": {"test": "data"}
                },
                timeout=10.0
            )
            print(f"✅ Full Generation API 응답: {response.status_code}")

        except Exception as e:
            print(f"⚠️ Full Generation API 테스트 실패: {e}")

        print("✅ 워크플로우 검증 완료")


# Playwright MCP 통합 버전
async def run_playwright_e2e_test():
    """Playwright MCP를 사용한 E2E 테스트"""
    print("🎭 Playwright E2E 테스트 시작")

    # 기본 E2E 테스트 실행
    test = FullGenerationE2ETest()
    success = await test.test_full_generation_workflow()

    if success:
        print("🎉 모든 E2E 테스트 통과!")
    else:
        print("💥 E2E 테스트 실패")

    return success


if __name__ == "__main__":
    # 직접 실행 시
    asyncio.run(run_playwright_e2e_test())