from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="the-junior-associate",
    version="1.0.0",
    author="The Junior Associate Contributors",
    author_email="contributors@thejuniorassociate.org",
    description="A polished Python library for scraping legal case law from multiple jurisdictions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gongahkia/the-junior-associate",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Legal Industry",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "junior-associate=the_junior_associate.cli:main",
        ],
    },
    keywords="legal case law scraping court judgments research",
    project_urls={
        "Bug Reports": "https://github.com/gongahkia/the-junior-associate/issues",
        "Source": "https://github.com/gongahkia/the-junior-associate",
        "Documentation": "https://the-junior-associate.readthedocs.io/",
    },
)