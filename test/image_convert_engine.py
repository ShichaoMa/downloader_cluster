# -*- coding:utf-8 -*-
import sys
from argparse import ArgumentParser

from pymongo import MongoClient
from pymongo.errors import CursorNotFound

sys.path.append("../tools")
from log_to_kafka import Logger
from MultiThreadClosing import MultiThreadClosing
from global_constant import G_ALL_DOMAINS, G_DICT_QUERY_PARAMETER
from image_convert import ImageConvert


class ImageConvertEngine(Logger, MultiThreadClosing):

    def __init__(self, settings=None, start_time=None, end_time=None, domain=None):
        self.name = "image_convert_engine"
        Logger.__init__(self, settings)
        self.set_logger()
        MultiThreadClosing.__init__(self)
        self.domain = domain
        self.start_time = start_time
        self.end_time = end_time
        self.connection = MongoClient(self.settings.get("MONGODB_SERVER"), self.settings.get("MONGODB_PORT"))
        self.products = self.connection.products
        self.documents = self.documents_from_mongodb()
        self.IC = ImageConvert(settings)
        self.IC.set_logger(self.logger)

    @classmethod
    def parse_args(cls):
        parser = ArgumentParser()
        parser.add_argument("-d", "--domain", dest="domain", choices=G_ALL_DOMAINS, required=True)
        parser.add_argument("--settings", dest="settings", default="settings.py")
        parser.add_argument("-s", "--start-time", dest="start_time", required=True)
        parser.add_argument("-e", "--end-time", dest="end_time", required=True)
        return cls(**vars(parser.parse_args()))

    def start(self):
        count = self.get_documents_count_from_mongodb()
        for index, document in enumerate(self.documents):
            result = self.IC.process_image(self.domain, document)
            self.logger.debug("process_image: %d/%d. result:%s" % (index + 1, count, result))
            if not self.alive:
                self.logger.debug('break. ')
                break
        else:
            self.logger.debug('finished. ')

    def get_documents_count_from_mongodb(self):
        return self.products[self.domain].find({"timestamp": {"$gte": self.start_time, "$lte": self.end_time}}).count()

    def documents_from_mongodb(self):
        collection = self.products[self.domain]
        query_parameter1 = {"timestamp": {"$gte": self.start_time, "$lte": self.end_time}}
        query_parameter2 = G_DICT_QUERY_PARAMETER[self.domain]

        done = False
        skip_delta = 0
        while not done:
            cursor = collection.find(query_parameter1, query_parameter2)
            cursor.skip(skip_delta)
            try:
                for document in cursor:
                    skip_delta += 1
                    yield document
                done = True
            except CursorNotFound, e:
                self.logger.error(e.message)


if __name__ == "__main__":
    ImageConvertEngine.parse_args().start()



