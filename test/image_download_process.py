# -*- coding:utf-8 -*-
import json

from downloader_cluster import MultiDownloadProcess


class ImageDownloadProcess(MultiDownloadProcess):

    name = "image_download_process"


    def __init__(self, settings):
        super(ImageDownloadProcess, self).__init__(settings)

    def decode(self, item):
        return map(lambda x: (x.get('url'), x.get('filename'), x.get('path')), json.loads(item)["images"])

    def callback(self, item, flag):
        pass

if __name__ == "__main__":
    IC = ImageDownloadProcess.parse_args()
    IC.is_small()
    IC.start()