# -*- coding:utf-8 -*-
import sys
import json
from threading import  RLock

from kafka.client import KafkaClient
from kafka.producer import SimpleProducer
sys.path.append("../downloader_cluster")
from multi_download_process import MultiDownloadProcess
from image_convert import ImageConvert


class ImageConvertProcess(MultiDownloadProcess):

    name = "image_convert_process"

    topic_name = "jay.crawled_firehose_images"

    def __init__(self, settings):
        super(ImageConvertProcess, self).__init__(settings)
        self.kafka_client = KafkaClient(self.settings.get("KAFKA_HOSTS"))
        self.kafka_client.ensure_topic_exists(self.topic_name)
        self.producer = SimpleProducer(self.kafka_client)
        self.lock = RLock()
        self.IC = ImageConvert(settings)
        self.IC.set_logger(self.logger)

    def decode(self, item):
        return map(lambda x:(x.get('url'), x.get('filename'), x.get('path')), json.loads(item)["images"])

    def callback(self, item, flag):
        #print "download finish. flag:%s"%flag
        with self.lock:
            if flag:
                item = json.loads(item)
                self.logger.debug("process in pan. ")
                if item.get("meta", {}).get("spiderid") != "loco_amazon":
                    item["pan_result"] = self.IC.process_image(item.get("meta", {}).get("collection_name"), item)
                    self.logger.debug("finish process in pan, result:%s"%item["pan_result"])
                else:
                    self.logger.info("ignore loco_amazon images. ")
                self.producer.send_messages(self.topic_name, json.dumps(item))
                self.logger.debug("send item to kafka. ")
            else:
                self.logger.error("download failed")

if __name__ == "__main__":
    IC = ImageConvertProcess.parse_args()
    IC.is_small()
    IC.start()