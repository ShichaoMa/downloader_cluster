# -*- coding:utf-8 -*-


# 使用多线程下载的最小size，也就是说小于此数的文件不会使用多线程
MIN_SIZE = 1024000
# 多线程下载时最大线程数
THREAD_COUNT = 1
# 下载文件保存路径
DIR = "."
# 分布式下载时，监听的redis list 的 key
QUEUE_KEY = "download_url_queue"
# 分布式下载时，同时下载的文件数
CONCURRENT_DOWNLOAD_COUNT = 5
# 自定义配置
KAFKA_HOSTS="192.168.200.58:9092"
# 日志级别 日志相关的其它参数请参见 default_setting.py
LOG_LEVEL = 'DEBUG'
# 分布式下载时 redis host
REDIS_HOST = "127.0.0.1"
# 分布式下载时 redis port
REDIS_PORT = 6379