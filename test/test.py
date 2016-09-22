# -*- coding:utf-8 -*-
import json
from downloader_cluster import MultiDownloadProcess


class Test(MultiDownloadProcess):

    name = "test"

    def decode(self, item):
        """
        从redis中获取item, 解析item得到url, filename, path组成的列表
        :param item:
        :return: [(url1, filename1, path1), (url2, filename2, path2), ...]
        """
        return json.loads(item)

    def callback(self, item, flag):
        """
        每个item执行完毕后的回调函数
        :param item:
        :param flag: 下载成功与否标志，item中若有一组下载，只要成功一个就算成功
        :return:
        """
        print item, flag


if __name__ == "__main__":
    t = Test.parse_args()
    t.is_small() # 对于可不使用多线程下载的小文件，调用此函数可简化下载步骤
    t.start()
