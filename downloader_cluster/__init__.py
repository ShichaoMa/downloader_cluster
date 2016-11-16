# -*- coding:utf-8 -*-
from .downloader import DownloaderEngine
from multi_download_process import MultiDownloadProcess


def start():
    DownloaderEngine.parse_args()