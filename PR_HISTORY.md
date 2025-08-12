# TestscenarioMaker 모노레포 PR 히스토리

> 이 문서는 기존 단일 저장소에서 병합된 PR들의 히스토리를 추적합니다.  
> **모노레포 이후의 PR들은 GitHub PR 탭에서 확인할 수 있습니다.**

## 📍 빠른 참조
- [Backend PR 히스토리](#-backend-testscenariomaker-pr-히스토리)
- [CLI PR 히스토리](#-cli-testscenariomaker-cli-pr-히스토리)  
- [Git Notes 사용법](#-git-notes-사용법)
- [모노레포 병합 정보](#-모노레포-병합-정보)

---

## 🌐 Backend (TestscenarioMaker) PR 히스토리

### 🔥 주요 기능 업데이트 PR

#### #36: Develop - 주요 기능 업데이트 및 CLI 연동 지원 (2025-08-10)
- **커밋**: `cb51f1a1c0264fc6c451966f7c5a8faf40ff53e6`
- **원본 저장소**: [recrash/TestscenarioMaker](https://github.com/recrash/TestscenarioMaker)
- **원본 PR**: https://github.com/recrash/TestscenarioMaker/pull/36
- **주요 변경사항**:
  - 🔧 엑셀 다운로드 기능 버그 수정
  - 💾 피드백 초기화 및 백업 시스템 구현
  - 🔄 FeedbackManager 피드백 관리 메서드 추가
  - 🌐 CLI 통합을 위한 V2 API 엔드포인트
  - 📊 카테고리별 피드백 분석 기능
- **Git Notes**: `git notes show cb51f1a` 로 상세 정보 확인

#### #30: Release - 주요 기능 업데이트 및 CLI 연동 지원 (2025-08-07)
- **커밋**: `6f8b7a0649192b3d675876bce43dc6559afcf7ad`
- **원본 저장소**: [recrash/TestscenarioMaker](https://github.com/recrash/TestscenarioMaker)
- **주요 변경사항**:
  - 🔧 엑셀 다운로드 기능 버그 수정
  - 💾 피드백 초기화 및 백업 시스템 구현
  - 🔄 CLI 연동 지원 기능
- **Git Notes**: `git notes show 6f8b7a0` 로 상세 정보 확인

#### #24: Release - 피드백 시스템 및 로깅 시스템 완성 (2025-08-04)
- **커밋**: `3d88b276a85d2d2b0a6906b11f748e3ee71576e8`
- **원본 저장소**: [recrash/TestscenarioMaker](https://github.com/recrash/TestscenarioMaker)
- **주요 변경사항**:
  - 📊 피드백 시스템 완성
  - 📝 로깅 시스템 구현
  - 🔄 develop → main 브랜치 머지
- **Git Notes**: `git notes show 3d88b27` 로 상세 정보 확인

#### #19: React+FastAPI 마이그레이션 후속 정리 (2025-08-04)
- **커밋**: `a67e4341f8c94c8d965881c7e4c2a0c0c0a0a0a0`
- **원본 저장소**: [recrash/TestscenarioMaker](https://github.com/recrash/TestscenarioMaker)
- **주요 변경사항**:
  - 🚀 Streamlit → React+FastAPI 마이그레이션 완성
  - 🧹 후속 정리 작업 완료
  - 🏗️ 아키텍처 개선
- **Git Notes**: `git notes show a67e434` 로 상세 정보 확인

---

## ⚡ CLI (TestscenarioMaker-CLI) PR 히스토리

### 🌐 브라우저 통합 및 문서화 PR

#### #19: README.md 전면 개편 및 개선 (2025-08-08)
- **커밋**: `ec6051342957b2ed966b7c5a8faf40ff53e6`
- **원본 저장소**: [recrash/TestscenarioMaker-CLI](https://github.com/recrash/TestscenarioMaker-CLI)
- **원본 PR**: https://github.com/recrash/TestscenarioMaker-CLI/pull/19
- **주요 변경사항**:
  - 📚 README.md 전면 개편 (626줄 → 229줄로 최적화)
  - 🌐 `testscenariomaker://` URL 프로토콜 지원
  - 🍎 macOS 브라우저 샌드박스 우회 헬퍼 앱 시스템
  - 🔗 크로스플랫폼 브라우저 통합
  - 📦 설치 프로그램 개선
- **Git Notes**: `git notes show ec60513` 로 상세 정보 확인

---

## 🔍 Git Notes 사용법

### 특정 커밋의 상세 PR 정보 확인
```bash
# Backend 주요 커밋
git notes show cb51f1a  # PR #36: CLI 연동 및 주요 업데이트
git notes show 6f8b7a0  # PR #30: 기능 업데이트 Release
git notes show 3d88b27  # PR #24: 피드백/로깅 시스템 완성
git notes show a67e434  # PR #19: React+FastAPI 마이그레이션

# CLI 주요 커밋  
git notes show ec60513  # PR #19: README 개편 및 브라우저 통합
```

### 모든 Notes와 함께 로그 확인
```bash
# Notes와 함께 전체 히스토리 보기
git log --show-notes --oneline

# 특정 서브프로젝트만 확인
git log --show-notes --oneline backend/
git log --show-notes --oneline cli/
```

### Notes 검색
```bash
# PR 관련 Notes 검색
git log --grep="Original-PR" --show-notes

# 특정 저장소 관련 검색
git log --grep="TestscenarioMaker" --show-notes
git log --grep="CLI" --show-notes
```

---

## 📦 모노레포 병합 정보

### Git Subtree 병합 내역
- **Backend 병합**: 2025-08-12
  - 소스 저장소: `https://github.com/recrash/TestscenarioMaker.git`
  - 병합 커밋: `752e904` - "Add 'backend/' from commit 'cb51f1a...'"
  - 보존된 히스토리: 완전한 커밋 히스토리 및 PR 기록

- **CLI 병합**: 2025-08-12  
  - 소스 저장소: `https://github.com/recrash/TestscenarioMaker-CLI.git`
  - 병합 커밋: `67fb5de` - "Add 'cli/' from commit 'ec60513...'"
  - 보존된 히스토리: 완전한 커밋 히스토리 및 PR 기록

### 히스토리 보존 방식
- **Git Subtree**: 원본 저장소의 모든 커밋 히스토리 보존
- **Git Notes**: 주요 PR 정보를 메타데이터로 추가
- **PR_HISTORY.md**: 사용자 친화적 히스토리 문서화

---

## 📈 통계 정보

### Backend (TestscenarioMaker)
- **주요 PR**: 4개 (PR #36, #30, #24, #19)
- **개발 기간**: 2025년 7월 ~ 8월
- **주요 마일스톤**: Streamlit → React+FastAPI 마이그레이션, CLI 연동, 피드백 시스템

### CLI (TestscenarioMaker-CLI)  
- **주요 PR**: 1개 (PR #19)
- **개발 기간**: 2025년 8월
- **주요 마일스톤**: 브라우저 통합, URL 프로토콜, macOS 헬퍼 앱

---

> **📌 참고**: 이 문서는 모노레포 병합 시점(2025-08-12) 기준으로 작성되었습니다.  
> 향후 PR들은 이 저장소의 GitHub PR 탭에서 직접 확인할 수 있습니다.