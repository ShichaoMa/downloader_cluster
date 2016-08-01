# downloader_cluster
一个简单的支持多线程，断点续传及分布式的下载器


ubuntu

INSTALL

    git clone https://github.com/ShichaoMa/downloader_cluster.git

START

    ```
        ubuntu@dev:~/myprojects/downloader_cluster$ python downloader.py -h
        usage: downloader.py [-h] {start,reload} ...

        positional arguments:
          {start,reload}
            start         start download a file.
            reload        continue downlaod a file.

        optional arguments:
          -h, --help      how this help message and exit
        Command 'start'
        usage: downloader.py start [-h] [-s SETTINGS] -u URL -f FILENAME

        Command 'reload'
        usage: downloader.py reload [-h] [-s SETTINGS] -u URL -f FILENAME

    ```

    demo1

    ```
        # 普通下载
        python downloader.py start -u "https://download.jetbrains.8686c.com/python/pycharm-community-2016.2.tar.gz" -f  test.tar.gz
        # 断点续传(服务器需要提供支持)
        python downloader.py reload -u "https://download.jetbrains.8686c.com/python/pycharm-community-2016.2.tar.gz" -f  test.tar.gz

    ```

    demo2

    ```
        # 分布式下载
        # 向redis队列中发布下载任务
        # 实现自定义分布式下载器
        # 参见test.py

    ```