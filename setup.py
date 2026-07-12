from setuptools import setup, find_packages, Extension
try:
    from Cython.Build import cythonize
    use_cython = True
except ImportError:
    use_cython = False

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
    version="1.5.0",
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
