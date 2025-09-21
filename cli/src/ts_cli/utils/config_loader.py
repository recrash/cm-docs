"""
설정 로더 모듈

configparser를 사용하여 INI 형식의 설정 파일을 읽고 관리합니다.
"""

import os
import sys
import logging
from pathlib import Path
from configparser import ConfigParser
from typing import Dict, Any, Optional, Union


logger = logging.getLogger(__name__)


def get_bundled_config_path() -> Optional[Path]:
    """PyInstaller 번들에서 config 파일 경로 반환"""
    try:
        if hasattr(sys, '_MEIPASS'):
            bundle_dir = Path(sys._MEIPASS)
            print(f"[DEBUG] PyInstaller bundle detected: {bundle_dir}")
            
            # 디렉터리 구조 상세 확인
            logger.info(f"=== PyInstaller 번들 디렉터리 구조 분석 ===")
            logger.info(f"Bundle directory: {bundle_dir}")
            
            if bundle_dir.exists():
                logger.info("Bundle directory contents:")
                for item in bundle_dir.iterdir():
                    logger.info(f"  {item.name} ({'DIR' if item.is_dir() else 'FILE'})")
                    if item.name == 'config' and item.is_dir():
                        logger.info(f"  Config directory contents:")
                        for subitem in item.iterdir():
                            logger.info(f"    {subitem.name} ({'DIR' if subitem.is_dir() else 'FILE'}) - Size: {subitem.stat().st_size if subitem.is_file() else 'N/A'}")
                            
                            # config.ini 파일의 내용까지 확인
                            if subitem.name == 'config.ini' and subitem.is_file():
                                try:
                                    content = subitem.read_text(encoding='utf-8')
                                    logger.info(f"    config.ini content preview:")
                                    for line_num, line in enumerate(content.split('\n')[:10], 1):
                                        logger.info(f"      {line_num:2d}: {line}")
                                except Exception as e:
                                    logger.error(f"    Failed to read config.ini content: {e}")
            
            # 기존 경로들 확인
            possible_paths = [
                bundle_dir / "config" / "config.ini",
                bundle_dir / "config.ini",
                bundle_dir / "config"
            ]
            
            # 루트 디렉토리의 모든 .ini 파일도 확인
            for ini_file in bundle_dir.glob("*.ini"):
                if ini_file.is_file() and ini_file.name.endswith('.ini'):
                    print(f"[DEBUG] Found .ini file in bundle root: {ini_file.name}")
                    possible_paths.insert(0, ini_file)  # 우선순위 높게 설정
            
            for path in possible_paths:
                logger.info(f"Checking path: {path}")
                print(f"[DEBUG] Checking bundled config path: {path}")
                if path.exists():
                    logger.info(f"  EXISTS - Type: {'DIR' if path.is_dir() else 'FILE'}")
                    print(f"[DEBUG]   Path exists! Is file: {path.is_file()}")
                    if path.is_file():
                        logger.info(f"  File size: {path.stat().st_size} bytes")
                        print(f"[DEBUG]   Returning bundled config: {path}")
                        return path
                    else:
                        logger.info(f"  Is directory, not file")
                else:
                    logger.info(f"  Does not exist")
                    
        return None
    except Exception as e:
        logger.debug(f"번들된 설정 파일 검색 중 오류: {e}")
        print(f"[DEBUG] 번들된 설정 파일 검색 중 오류: {e}")
        return None


class ConfigLoader:
    """
    설정 파일 로더 클래스

    INI 형식의 설정 파일을 읽고 설정값을 제공합니다.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        ConfigLoader 초기화

        Args:
            config_path: 설정 파일 경로 (None이면 기본 경로 사용)
        """
        self.config = ConfigParser()
        self.config_path = self._resolve_config_path(config_path)
        self._load_config()

    def _resolve_config_path(self, config_path: Optional[Path]) -> Path:
        """
        설정 파일 경로 결정

        Args:
            config_path: 사용자 지정 설정 파일 경로

        Returns:
            최종 설정 파일 경로
        """
        if config_path:
            return config_path

        # 1순위: PyInstaller로 번들된 설정 파일 (macOS/Windows 공통)
        bundled_config = get_bundled_config_path()
        if bundled_config:
            return bundled_config

        # 2순위: 현재 작업 디렉토리의 config.ini 확인
        current_config = Path.cwd() / "config.ini"
        if current_config.exists():
            return current_config

        # 3순위: 패키지 내의 기본 config 디렉토리 확인 (개발환경)
        package_root = Path(__file__).parent.parent.parent.parent
        default_config = package_root / "config" / "config.ini"
        if default_config.exists():
            return default_config

        # 4순위: config 디렉토리의 기본 설정 파일 (개발환경)
        config_dir = package_root / "config"
        if config_dir.exists():
            return config_dir / "config.ini"

        # 5순위: Windows 배포 환경 설정 파일 경로 (Windows 전용)
        deploy_config = Path("C:/deploys/data/cli/config.ini")
        if deploy_config.exists():
            return deploy_config

        # 최후의 수단: Windows 배포 환경 경로에 config.ini 생성 (권한 문제 방지)
        return deploy_config

    def _load_config(self) -> None:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                self.config.read(self.config_path, encoding="utf-8")
                logger.info(f"설정 파일 로드됨: {self.config_path}")
            else:
                logger.warning(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
                self._create_default_config()

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            self._load_default_values()

    def _create_default_config(self) -> None:
        """기본 설정 파일 생성"""
        try:
            # 설정 디렉토리 생성
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # 기본 설정 값 설정
            self._load_default_values()

            # 설정 파일 저장
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)

            logger.info(f"기본 설정 파일 생성됨: {self.config_path}")

        except Exception as e:
            logger.error(f"기본 설정 파일 생성 실패: {e}")

    def _get_default_api_url(self) -> str:
        """
        개발/운영 환경에 따른 기본 API URL 결정
        
        1. localhost:8000 서버 감지 시 → http://localhost:8000
        2. webservice/config.json의 base_url 사용 (폐쇄망 대응)
        3. 최종 fallback → https://cm-docs.cloud
        
        Returns:
            환경에 맞는 API 기본 URL
        """
        import socket
        import json
        
        try:
            # 1. localhost:8000 연결 테스트로 로컬 개발서버 감지
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1초 타임아웃
            result = sock.connect_ex(('localhost', 8000))
            sock.close()
            
            if result == 0:
                logger.debug("로컬 개발서버 감지됨, localhost API 사용")
                return "http://localhost:8000"
            
            # 2. webservice/config.json에서 base_url 읽기
            try:
                # CLI 프로젝트에서 webservice 설정 파일 경로 찾기
                cli_root = Path(__file__).parent.parent.parent.parent
                webservice_config = cli_root.parent / "webservice" / "config.json"
                
                if webservice_config.exists():
                    with open(webservice_config, 'r', encoding='utf-8') as f:
                        webservice_data = json.load(f)
                        base_url = webservice_data.get('base_url')
                        if base_url:
                            logger.debug(f"webservice 설정에서 base_url 사용: {base_url}")
                            return base_url
                            
            except Exception as e:
                logger.debug(f"webservice 설정 읽기 실패: {e}")
            
            # 3. 최종 fallback
            logger.debug("fallback으로 운영 서버 사용")
            return "https://cm-docs.cloud"
                
        except Exception as e:
            logger.debug(f"서버 감지 실패, fallback 사용: {e}")
            return "https://cm-docs.cloud"

    def _load_default_values(self) -> None:
        """기본 설정 값 로드"""
        # PyInstaller로 빌드된 환경에서는 동적 URL 감지 비활성화
        if getattr(sys, 'frozen', False):
            # 빌드된 환경에서는 고정된 fallback URL 사용
            default_base_url = "https://cm-docs.cloud"
        else:
            # 개발 환경에서만 동적 URL 감지 사용
            default_base_url = self._get_default_api_url()
        
        # API 설정
        self.config["api"] = {
            "base_url": default_base_url,
            "timeout": "30",
            "max_retries": "3",
            "retry_delay": "1.0",
        }

        # CLI 설정
        self.config["cli"] = {
            "default_output_format": "text",
            "verbose": "false",
            "show_progress": "true",
        }

        # 로깅 설정
        from .logger import get_default_log_path
        default_log_path = str(get_default_log_path())
        
        self.config["logging"] = {
            "level": "INFO",
            "format": "%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s",
            "file_enabled": "false",
            "file_path": default_log_path,
        }

        # VCS 설정
        self.config["vcs"] = {
            "git_timeout": "30",
            "max_diff_size": "1048576",  # 1MB
        }

    def get(
        self, section: str, key: str, default: Any = None, value_type: type = str
    ) -> Any:
        """
        설정 값 조회

        Args:
            section: 설정 섹션명
            key: 설정 키명
            default: 기본값
            value_type: 반환값 타입

        Returns:
            설정 값 (지정된 타입으로 변환됨)
        """
        try:
            if not self.config.has_section(section):
                return default

            if not self.config.has_option(section, key):
                return default

            # logging.format은 raw로 읽기 (문자열 보간 방지)
            if section == "logging" and key == "format":
                value = self.config.get(section, key, raw=True)
            else:
                value = self.config.get(section, key)

            # 타입 변환
            if value_type == bool:
                return value.lower() in ("true", "1", "yes", "on")
            elif value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            else:
                return value

        except Exception as e:
            logger.warning(f"설정 값 조회 실패 ({section}.{key}): {e}")
            return default

    def set(self, section: str, key: str, value: Any) -> None:
        """
        설정 값 설정

        Args:
            section: 섹션명
            key: 설정 키
            value: 설정 값
        """
        section_added = False
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)
                section_added = True

            self.config.set(section, key, str(value))

        except Exception as e:
            logger.error(f"설정 값 설정 실패 ({section}.{key}): {e}")
            # 예외 발생 시 추가된 섹션 제거
            if section_added:
                try:
                    self.config.remove_section(section)
                except Exception:
                    pass  # 섹션 제거 실패는 무시
            return

    def save(self) -> bool:
        """
        설정 파일 저장

        Returns:
            저장 성공 여부
        """
        try:
            # 디렉토리가 없으면 생성
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)
            logger.info(f"설정 파일 저장됨: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
            return False

    def get_section(self, section: str) -> Dict[str, str]:
        """
        섹션 전체 조회

        Args:
            section: 섹션명

        Returns:
            섹션의 모든 설정을 담은 딕셔너리
        """
        try:
            if self.config.has_section(section):
                return dict(self.config.items(section))
            return {}

        except Exception as e:
            logger.warning(f"섹션 조회 실패 ({section}): {e}")
            return {}

    def get_all_sections(self) -> Dict[str, Dict[str, str]]:
        """
        모든 섹션 조회

        Returns:
            모든 설정을 담은 중첩 딕셔너리
        """
        result = {}
        for section_name in self.config.sections():
            result[section_name] = self.get_section(section_name)
        return result


# 전역 설정 로더 인스턴스
_config_loader: Optional[ConfigLoader] = None


def load_config(config_path: Optional[Union[str, Path]] = None) -> ConfigLoader:
    """
    설정 로더 초기화 및 반환

    Args:
        config_path: 설정 파일 경로

    Returns:
        ConfigLoader 인스턴스
    """
    global _config_loader

    if _config_loader is None or config_path is not None:
        path = Path(config_path) if config_path else None
        _config_loader = ConfigLoader(path)

    return _config_loader


def get_config() -> ConfigLoader:
    """
    현재 설정 로더 인스턴스 반환

    Returns:
        ConfigLoader 인스턴스

    Raises:
        RuntimeError: 설정 로더가 초기화되지 않은 경우
    """
    if _config_loader is None:
        return load_config()
    return _config_loader


def get_api_config() -> Dict[str, Any]:
    """
    API 설정 반환

    Returns:
        API 설정 딕셔너리
    """
    config = get_config()
    return {
        "base_url": config.get("api", "base_url"),
        "timeout": config.get("api", "timeout", 30, int),
        "max_retries": config.get("api", "max_retries", 3, int),
        "retry_delay": config.get("api", "retry_delay", 1.0, float),
    }


def get_cli_config() -> Dict[str, Any]:
    """
    CLI 설정 반환

    Returns:
        CLI 설정 딕셔너리
    """
    config = get_config()
    return {
        "default_output_format": config.get("cli", "default_output_format", "text"),
        "verbose": config.get("cli", "verbose", False, bool),
        "show_progress": config.get("cli", "show_progress", True, bool),
    }
