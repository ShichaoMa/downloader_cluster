# -*- coding:utf-8 -*-
import time
import sys
from redis import Redis
from Queue import Queue, Empty
from argparse import ArgumentParser
from threading import Thread, current_thread
sys.path.append("../tools")
from MultiThreadClosing import MultiThreadClosing
from log_to_kafka import Logger
from downloader import DownloaderEngine


class MultiDownloadProcess(Logger, MultiThreadClosing):

    name = "multidownload_process"

    def __init__(self, settings):
        self.settings_file = settings
        Logger.__init__(self, settings)
        self.set_logger()
        MultiThreadClosing.__init__(self)
        self.de_queue = Queue()
        self.redis_conn = Redis(self.settings.get("REDIS_HOST"),
                                self.settings.get("REDIS_PORT"))
        self.small = False

    @classmethod
    def parse_args(cls):
        parser = ArgumentParser()
        parser.add_argument("-s", "--settings", dest="settings", default="settings.py")
        return cls(**vars(parser.parse_args()))

    def is_small(self):
        self.small=True

    def callback(self, item, flag):
        """
        callback called when download is finished.
        :return:
        """
        raise NotImplementedError()

    def decode(self, item):
        """
        redis pop out to got url, filename, directory
        :param item:
        :return: (url, filename, directory)
        """
        raise NotImplementedError()

    def processing(self, de, url_paths, item):
        if self.small:
            downloader = "download_small_file"
        else:
            downloader = "start"
        flag = False
        try:
            for url, filename, path in url_paths:
                result = getattr(de, downloader)(url=url, filename=filename, path=path)
                flag = flag or result
            self.logger.debug("download finished, success:%s"%flag)
            self.callback(item, flag)
        finally:
            self.de_queue.put(de)
            try:
                self.threads.remove(current_thread())
            except ValueError:
                pass
            self.logger.debug("the count of thread which is alive is %s. "%len(self.threads))

    def start(self):
        self.logger.debug("start process %s"%self.name)
        concurrent_download_count = self.settings.get("CONCURRENT_DOWNLOAD_COUNT", 10)
        for i in range(concurrent_download_count):
            DE = DownloaderEngine(self.settings_file, signal_open=False)
            DE.set_logger(self.logger)
            self.de_queue.put(DE)
        self.logger.debug("setup %s des"%concurrent_download_count)
        while self.alive:
            item = self.redis_conn.lpop(self.settings.get("QUEUE_KEY"))
            if not item:
                self.logger.debug("got no message...")
                time.sleep(1)
                continue
            self.logger.debug("%s tasks  to be continue..."%self.redis_conn.llen(self.settings.get("QUEUE_KEY")))
            url_paths = self.decode(item)
            while True:
                try:
                    DE = self.de_queue.get_nowait()
                    th = Thread(target=self.processing, args=(DE, url_paths, item))
                    self.set_force_interrupt(th)
                    th.start()
                except Empty:
                    time.sleep(1)
                else:
                    break
        while True:
            if filter(lambda x:x.is_alive(), self.threads):
                time.sleep(1)
            else:
                break


if __name__ == "__main__":
    MDP = MultiDownloadProcess.parse_args()
    MDP.start()


