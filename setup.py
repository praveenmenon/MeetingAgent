"""
Setup configuration for Meeting Agent
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="meeting-agent",
    version="1.0.0",
    author="Meeting Agent Team",
    author_email="team@meetingagent.dev",
    description="AI-powered meeting transcription and task management system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/meeting-agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "meeting-agent=meeting_agent.cli:main",
            "meeting-worker=meeting_agent.worker:main",
            "meeting-config=meeting_agent.config_manager:main",
            "meeting-monitor=meeting_agent.monitor:main",
        ],
    },
    include_package_data=True,
    package_data={
        "meeting_agent": ["config/*.yaml", "templates/*.txt"],
    },
)