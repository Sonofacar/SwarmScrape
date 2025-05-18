# setup.py
#
# Copyright (C) 2025 Carson Buttars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

# Get version from the version.py or directly define it here
VERSION = "0.1.0"

setup(
    name="SwarmScrape",
    version=VERSION,
    description="A pooled proxy server designed for simple webscraping.",
    author="Carson Buttars",
    author_email="carsonbuttars13@gmail.com",
    url="https://github.com/sonofacar/SwarmScrape",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "cachetools",
        "nodriver",
        "requests",
        "bs4",
    ],
    entry_points={
        "console_scripts": ["SwarmScrape = SwarmScrape:run_proxy"],
    },
    license="GPLv3",
    license_files=["LICENSE"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    python_requires=">=3.7",
)

