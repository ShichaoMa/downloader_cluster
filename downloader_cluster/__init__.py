# -*- coding:utf-8 -*-
from .downloader import DownloaderEngine
from multi_download_process import MultiDownloadProcess


VERSION = '1.0.6'

AUTHOR = "cn"

AUTHOR_EMAIL = "308299269@qq.com"

URL = "https://www.github.com/ShichaoMa/downloader_cluster"

NAME = "downloader-cluster"

DESCRIPTION = "一个简单的支持多线程，断点续传及分布式的下载器。 "


def start():
    DownloaderEngine.parse_args()