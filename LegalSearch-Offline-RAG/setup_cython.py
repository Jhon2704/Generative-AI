# -*- coding: utf-8 -*-
"""
setup_cython.py - Compila los modulos de src/ a extensiones binarias .pyd
Uso: python setup_cython.py build_ext --inplace
"""

import glob
from setuptools import setup
from Cython.Build import cythonize

modules = [
    m for m in glob.glob("src/*.py")
    if "__init__" not in m
]

setup(
    ext_modules=cythonize(
        modules,
        language_level=3,
        compiler_directives={
            "always_allow_keywords": True,
            "embedsignature": False,
        },
        quiet=True,
    )
)
