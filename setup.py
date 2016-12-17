# -*- coding:utf-8 -*-
import codecs
import os
try:
    from setuptools import setup, find_packages
except:
    from distutils.core import setup

VERSION = '1.0.6'

AUTHOR = "cn"

AUTHOR_EMAIL = "308299269@qq.com"

URL = "https://www.github.com/ShichaoMa/downloader_cluster"

NAME = "downloader-cluster"

DESCRIPTION = "一个简单的支持多线程，断点续传及分布式的下载器。 "


def read(fname):
    return codecs.open(os.path.join(os.path.dirname(__file__), fname)).read()

LONG_DESCRIPTION = read("README.rst")

KEYWORDS = "downloader cluster download"

LICENSE = "MIT"

PACKAGES = ["downloader_cluster"]

setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    classifiers = [
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'downloader = downloader_cluster:start',
        ],
    },
    keywords = KEYWORDS,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    url = URL,
    license = LICENSE,
    packages = PACKAGES,
    install_requires=["multi-thread-closing", "log-to-kafka", "custom-redis"],
    include_package_data=True,
    zip_safe=True,
)