from setuptools import setup, find_packages

setup(
    name="sonic-boom",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "zeroconf>=0.132.0",
        "click>=8.1.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "sonic-boom=sonic_boom.cli:main",
        ],
    },
)
