# -*- coding:utf-8 -*-
import os
import re
import hashlib
import requests
import traceback

from Queue import Queue, Empty
from argparse import ArgumentParser, _HelpAction, _SubParsersAction
from threading import Thread, RLock
from urllib2 import urlopen, Request

from log_to_kafka import Logger
from multi_thread_closing import MultiThreadClosing


SEND_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    "Accept-Language": "en-US,en;q=0.5",
}


class ArgparseHelper(_HelpAction):
    """
        显示格式友好的帮助信息
    """

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, _SubParsersAction)]
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                print("Command '{}'".format(choice))
                print(subparser.format_usage())

        parser.exit()


class Downloader(Thread):

    def __init__(self, url, lock, start, end, fileobj, temp_file,
                 engine, queue, total_size, continue_support, timeout, buffer_size=102400):
        super(Downloader, self).__init__()
        self.engine = engine
        self.temp_file = temp_file
        self.lock = lock
        self.fileobj = fileobj
        self.buffer_size = buffer_size
        self.continue_support =  continue_support
        self.start_ = start
        self.end = end
        self.queue = queue
        self.total_size = total_size
        headers = SEND_HEADERS.copy()
        headers["Range"] = "bytes=%s-%s"%(self.start_, self.end)
        req = Request(url, headers=headers)
        self.downloader = urlopen(req, timeout=timeout)

    def run(self):
        data = self.downloader.read(self.buffer_size)
        while data and self.engine.alive:
            with self.lock:
                self.fileobj.seek(self.start_)
                self.fileobj.write(data)
                self.start_ += len(data)
                self.fileobj.flush()
            self.queue.put(len(data))
            data = self.downloader.read(self.buffer_size)

        if self.continue_support and self.start_ < (self.end or self.total_size):
            with self.lock:
                self.temp_file.write("%s|%s\n"%(self.start_, self.end))


class DownloaderEngine(Logger, MultiThreadClosing):

    def __init__(self, settings, url=None, filename=None, dir=".", **kwargs):
        self.name = "downloader"
        Logger.__init__(self, settings)
        self.url = url
        self.filename = filename
        self.dir = dir
        self.per = 0
        self.callback = None
        self.queue = Queue()
        self.lock = RLock()
        if kwargs.get("signal_open", True):
            MultiThreadClosing.__init__(self)

    def support_continue(self, url):
        send_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            "Accept-Language": "en-US,en;q=0.5",
            'Range': 'bytes=0-4'
        }
        r = None
        total = 0
        try:
            r = requests.get(url, headers=send_headers, timeout=self.settings.get("DOWNLOAD_TIMEOUT", 30))
            crange = r.headers['content-range']
            total = int(re.match(ur'^bytes 0-4/(\d+)$', crange).group(1))
            return total, True
        except:
            pass
        try:
            total = int(r.headers.get('Content-Length', 0))
        except:
            exit(0)
        return total, False

    def download_small_file(self, url, filename, path="."):
        try:
            if os.path.exists(path) and os.path.getsize(path):
                self.logger.debug("file is already exists. ")
                return True
            if filename:
                path = os.path.join(path, filename)
            index = path.rfind("/")
            if index == -1:
                index = path.rfind("\\")
            if path and not os.path.exists(path[:index]):
                try:
                    os.makedirs(path[:index])
                except OSError:
                    pass
            resp = requests.get(url=url, headers=SEND_HEADERS, stream=True, timeout=self.settings.get("DOWNLOAD_TIMEOUT", 30))
            with open(path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk)
                    f.flush()
            if os.path.getsize(path):
                return True
            else:
                return False
        except Exception:
            self.logger.error(traceback.format_exc())
            if os.path.exists(path):
                os.remove(path)
            return False

    def start(self, url=None, filename=None, path=None):
        self.logger.debug("start download. ")
        self.url = url or self.url
        self.filename = filename or self.filename or self.url[self.url.rfind("/")+1:]
        if path and not os.path.exists(path[:path.rfind("/")]):
            os.makedirs(path[:path.rfind("/")])
        self.dir = self.dir or self.settings.get("DIR")
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)
        self.logger.debug("filename is %s"%(self.filename or path))
        content_length, flag = self.support_continue(self.url)
        if not content_length:
            self.download_small_file(self.url, None, os.path.join(self.dir, self.filename))
            return
        self.logger.debug("the file %s is %.2fk. "%(self.url, content_length/(1024)))
        average_size = content_length/self.settings.get("THREAD_COUNT", 1)
        min_size = self.settings.get("MIN_SIZE", 1024000)
        if not flag:
            thread_count = 1
            average_size = content_length
        elif average_size < min_size:
            thread_count, _ = divmod(content_length, min_size)
            thread_count += 1
            average_size = min_size
        else:
            thread_count = self.settings.get("THREAD_COUNT", 1)
        self.logger.debug("start %s threads to download"%thread_count)
        downloaded_count = 0
        thread_list = []
        fileobj = open(path or "%s/%s"%(self.dir, self.filename), "wb")
        temp_file_name = self.sha1("%s_%s"%(self.filename, self.url))
        temp_file = open("%s/%s"%(self.dir, temp_file_name), "w")

        for i in range(thread_count):
            th = Downloader(self.url, self.lock,
                            i * average_size,
                            "" if i == thread_count-1 else (i+1)*average_size,
                            fileobj, temp_file, self, self.queue, content_length, flag, self.settings.get("DOWNLOAD_TIMEOUT", 30))
            thread_list.append(th)
            th.start()
            self.logger.debug("start thread %s"%th.getName())

        alive = True
        while alive:
            if not self._check_alive(thread_list):
                alive = False
            try:
                while True:
                    downloaded_count += self.queue.get_nowait()
            except Empty:
                if downloaded_count:
                    self.show_process_line(content_length, downloaded_count)
        temp_file.close()
        if fileobj.tell() == content_length:
            self.logger.debug("finished")
            os.remove("%s/%s"%(self.dir, temp_file_name))
        fileobj.close()

    def show_process_line(self, count, num):
        speed = num * 100.0 / count
        str_speed = "%.2f%%  " % speed
        try:
            print "\r", str_speed, int(speed) * 50 / 100 * '\033[42m \033[0m',
        except IOError:
            pass

    def _check_alive(self, thread_list):
        for t in thread_list:
            if t.is_alive():
                return True
        return False

    @classmethod
    def sha1(cls, x):
        return hashlib.sha1(x).hexdigest()

    def load(self, url, filename=None):
        temp_file_name = self.sha1("%s_%s"%(filename, url))
        self.dir = self.settings.get("DIR", ".")
        temp_path = "%s/%s"%(self.dir, temp_file_name)
        if os.path.exists(temp_path):
            lst = map(lambda x:x.strip().split("|"),
                      filter(lambda x:x.strip(), open(temp_path, "r")))
            if not lst:
                self.start(url, filename)
                return
            content_length, flag = self.support_continue(url)
            downloaded_count = 0
            thread_list = []
            fileobj = open("%s/%s" % (self.dir, self.filename), "r+")
            temp_file = open(temp_path, "wb")

            for i in lst:
                start = int(i[0])
                end = int(i[1] or 0)
                th = Downloader(url, self.lock, start, end or "",
                                fileobj, temp_file, self, self.queue, content_length, True)
                downloaded_count += start-end
                thread_list.append(th)
                th.start()
                self.logger.debug("start thread %s" % th.getName())

            alive = True
            while alive:
                if not self._check_alive(thread_list):
                    alive = False
                try:
                    while True:
                        downloaded_count += self.queue.get_nowait()
                except Empty:
                    self.show_process_line(content_length, downloaded_count)


            temp_file.close()
            if fileobj.tell() == content_length:
                self.logger.debug("finished")
                os.remove("%s/%s" % (self.dir, temp_file_name))
            fileobj.close()
            return
        self.start(url, filename)


    @classmethod
    def parse_args(cls):
        parser = ArgumentParser(add_help=False)
        parser.add_argument("-h", "--help", action=ArgparseHelper, help="how this help message and exit")
        base_parser = ArgumentParser(add_help=False)
        base_parser.add_argument("-s", "--settings", dest="settings", default="settings.py")
        base_parser.add_argument("-u", "--url", dest="url", required=True)
        base_parser.add_argument("-f", "--filename", dest="filename")
        sub_parser = parser.add_subparsers(dest="cmd")
        sub_parser.add_parser("start", parents=[base_parser], help="start download a file. ")
        sub_parser.add_parser("reload", parents=[base_parser], help="continue downlaod a file. ")

        args = parser.parse_args()
        DE = cls(args.settings, args.url, args.filename)
        DE.set_logger()
        if args.cmd == "start":
            DE.start()
        else:
            DE.load(args.url, args.filename)


if __name__ == "__main__":
    DownloaderEngine.parse_args()