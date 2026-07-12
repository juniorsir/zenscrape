# setup.py
import os
from setuptools import setup, find_packages, Extension

try:
    from Cython.Build import cythonize
    use_cython = True
except ImportError:
    use_cython = False

# Read the contents of your README file for the long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
long_description = ""
if os.path.exists(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()

# Define which modules to compile to binary
extensions = []
if use_cython:
    extensions = cythonize([
        "zenscrape/engine.py",
        "zenscrape/cli.py",
        "zenscrape/inspector.py",
        "zenscrape/models.py",
        "zenscrape/storage.py",
        "zenscrape/setup_env.py"
    ], compiler_directives={'language_level': "3"})

setup(
    name="zenscrape",
    version="1.5.2", # Incremented version
    
    # --- ADDED METADATA DETAILS ---
    author="Junior Sir",
    author_email="juniorsir011@gmail.com",
    description="An anonymous, async-first web scraping framework with Tor and WAF bypass features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/juniorsir/zenscrape",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    # ------------------------------

    packages=find_packages(),
    ext_modules=extensions if use_cython else [],
    install_requires=[
        "curl_cffi",
        "selectolax",
        "pydantic",
        "loguru",
        "fake-useragent"
    ],
    entry_points={
        'console_scripts': [
            'zenscrape=zenscrape.cli:main',
        ],
    },
)
