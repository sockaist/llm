from setuptools import setup, find_packages

setup(
    name="vectordb",
    version="2.0.0",
    description="Universal Vector Database Solution for AI Applications",
    author="Sockaist AI Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic>=2.0",
        "qdrant-client",
        "httpx",
        "requests",
        "python-dotenv",
        "pyyaml",
        "click",
        "structlog",  # If used, otherwise logging is standard
    ],
    entry_points={
        "console_scripts": [
            "vectordb=vectordb.cli.commands:cli",
        ],
    },
    python_requires=">=3.8",
)
