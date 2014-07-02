from setuptools import setup, find_packages
import os

version = '0.0.0'

setup(
    name='mkpi',
    version=version,
    author="John Carr",
    author_email="john.carr@unrouted.co.uk",
    packages=find_packages(),
    entry_points = """
      [console_scripts]
      mkpi = mkpi.__main__:main
    """
)
