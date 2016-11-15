# -*- coding:utf-8 -*-
import time
import traceback

from Queue import Queue, Empty
from argparse import ArgumentParser
from threading import Thread, current_thread

from multi_thread_closing import MultiThreadClosing
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
        if self.settings.get("CUSTOM_REDIS"):
            from custom_redis.client import Redis
        else:
            from redis import Redis
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
            t1 = time.time()
            length = len(url_paths)
            for index, (url, filename, path) in enumerate(url_paths):
                result = getattr(de, downloader)(url=url, filename=filename, path=path)
                self.logger.info("download process %s/%s completed"%(index+1, length))
                flag = flag or result
            t2 = time.time()
            self.logger.info("download finished, success:%s, seconds:%.4f"%(flag,  t2-t1))
            self.de_queue.put(de)
            self.callback(item, flag)
            self.logger.info("callback finished, seconds:%.4f"%(time.time()-t2))
        except Exception:
            self.logger.error(traceback.format_exc())
        finally:
            try:
                self.threads.remove(current_thread())
            except ValueError:
                pass
            self.logger.info("the count of thread which alives is %s. "%len(self.threads))

    def start(self):
        self.logger.debug("start process %s"%self.name)
        concurrent_download_count = self.settings.get("CONCURRENT_DOWNLOAD_COUNT", 10)
        for i in range(concurrent_download_count):
            DE = DownloaderEngine(self.settings_file, signal_open=False)
            DE.set_logger(self.logger)
            self.de_queue.put(DE)
        self.logger.debug("setup %s des"%concurrent_download_count)
        while self.alive:
            try:
                item = self.redis_conn.lpop(self.settings.get("QUEUE_KEY"))
            except Exception:
                self.logger.error("redis error %s"%traceback.format_exc())
                item = None
            if not item:
                self.logger.debug("got no message...")
                time.sleep(1)
                continue
            self.logger.debug("%s tasks  to be continue..."%self.redis_conn.llen(self.settings.get("QUEUE_KEY")))
            try:
                url_paths = self.decode(item)
            except Exception:
                self.logger.error(traceback.format_exc())
                url_paths = []
            while url_paths:
                try:
                    DE = self.de_queue.get_nowait()
                    th = Thread(target=self.processing, args=(DE, url_paths, item))
                    self.set_force_interrupt(th)
                    self.logger.debug("start a new thread. ")
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


