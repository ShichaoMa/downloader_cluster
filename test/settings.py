# -*- coding:utf-8 -*-

MONGODB_SERVER = "192.168.200.120"

# 分布式下载时，监听的redis list 的 key
QUEUE_KEY = "download_url_queue"
# 分布式下载时，同时下载的文件数
CONCURRENT_DOWNLOAD_COUNT = 40
# 自定义配置
KAFKA_HOSTS="192.168.200.58:9092"
# 日志级别 日志相关的其它参数请参见 default_setting.py
LOG_LEVEL = 'DEBUG'
# 分布式下载时 redis host
REDIS_HOST = "127.0.0.1"
# 分布式下载时 redis port
REDIS_PORT = 6379

CUSTOM_REDIS = True
