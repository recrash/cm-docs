#!/usr/bin/env python3
"""
TestscenarioMaker CLI 설치 스크립트
로컬 저장소 분석을 위한 크로스플랫폼 CLI 도구
"""

from setuptools import setup, find_packages
from pathlib import Path

# README 파일 읽기
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="testscenariomaker-cli",
    version="1.0.0",
    description="TestscenarioMaker를 위한 로컬 저장소 분석 CLI 도구",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="TestscenarioMaker Team",
    author_email="support@testscenariomaker.com",
    url="https://github.com/testscenariomaker/cli",
    
    # 패키지 설정
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # CLI 진입점 설정
    entry_points={
        "console_scripts": [
            "ts-cli=ts_cli.main:cli",
        ],
    },
    
    # Python 버전 요구사항
    python_requires=">=3.8",
    
    # 의존성
    install_requires=[
        "click>=8.0.0",
        "rich>=13.0.0",
        "httpx>=0.24.0",
        "tenacity>=8.0.0",
        "pathlib2>=2.3.0;python_version<'3.4'",
    ],
    
    # 개발 의존성
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "httpx-mock>=0.10.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "build": [
            "pyinstaller>=5.0.0",
            "nsis>=3.0.0;platform_system=='Windows'",
        ],
    },
    
    # 메타데이터
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Tools",
        "Topic :: System :: Archiving :: Backup",
    ],
    
    # 패키지 데이터
    include_package_data=True,
    package_data={
        "ts_cli": ["config/*.ini"],
    },
    
    # 키워드
    keywords="cli, git, repository, analysis, testscenariomaker",
    
    # 프로젝트 URL
    project_urls={
        "Bug Reports": "https://github.com/testscenariomaker/cli/issues",
        "Source": "https://github.com/testscenariomaker/cli",
        "Documentation": "https://docs.testscenariomaker.com/cli",
    },
)