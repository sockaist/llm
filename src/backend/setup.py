"""
Langchain 커스텀 구현 라이브러리 - 설치 스크립트
"""

from setuptools import setup, find_packages

setup(
    name="langchain_custom",
    version="0.1.0",
    author="Langchain Custom Implementation Team",
    author_email="example@example.com",
    description="Langchain의 주요 기능들을 파이썬으로 직접 구현한 라이브러리",
    long_description=open("documentation.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/langchain_custom",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "google-generativeai>=0.1.0",
        "pydantic>=1.8.0",
        "regex>=2021.4.4",
        "jinja2>=3.0.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.5b2",
            "isort>=5.9.1",
        ],
    },
)
