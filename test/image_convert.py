# -*- coding:utf-8 -*-
import os
import re
import traceback
import json
import subprocess
import itertools
from functools import wraps
from log_to_kafka import Logger



def exception_wrapper(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            return False
    return wrapper


class ImageConvert(Logger):

    name = "image_convert"
    g_requre_images_count = 6
    size_pattern = re.compile("\s(\d+)x(\d+)\s")

    def __init__(self, settings):
        super(ImageConvert, self).__init__(settings)
        self.image_funcs = [self.clip_center_50_percent_scale_to,
                            self.clip_north_west_75_percent_scale_to,
                            self.clip_south_east_75_percent_scale_to,
                            self.clip_west_or_north_scale_to,
                            self.clip_east_or_south_scale_to]

    def process_image(self, domain, document):
        return exception_wrapper(getattr(self, "_process_color_images_%s"%domain[4:]))(document)

    def get_image_local_abs_path(self, images, url):
        for i in images:
            if i['url'] == url:
                return i['path']
        self.logger.error("[error]: %s is not download!" % url)

    # 把原始图片缩放至800x800,缺失部分以白色填充
    def convert_to_800x800(self, image_src, image_dest):
        self.convert_to(image_src, image_dest, 800, 800)

    # 把原始图片缩放至640x640,缺失部分以白色填充
    def convert_to_640x640(self, image_src, image_dest):
        self.convert_to(image_src, image_dest, 640, 640)

    def convert_to_800x800_and_640x640(self, image_src, image_dest_800, image_dest_640):
        self.convert_to_800x800(image_src, image_dest_800)
        self.convert_to_640x640(image_src, image_dest_640)

    # 把原始图片缩放至800x800和640x640,缺失部分以白色填充
    def convert_to_800x800_and_640x640_and_150x150(self, image_src):
        self.convert_to_800x800_and_640x640(image_src, image_src[:image_src.find('.')] + '_800.jpg',
                                         image_src[:image_src.find('.')] + '_640.jpg')
        self.convert_to(image_src, image_src[:image_src.find('.')] + '_150.jpg', 150, 150)

    # 从中心截取 二分之一，缩放至 width x height
    def clip_center_50_percent_scale_to(self, image_src, image_dest, width, height, w, h):
        try:
            self.clip_scale_to(image_src, image_dest, width, height, "center", 0, 0, w / 2, h / 2)
        except IOError:
            self.logger.error("%s clip_center_50_percent_scale_to_800x800 error!" % image_src)

    # 从左上角截取四分之三，缩放至800x800
    def clip_north_west_75_percent_scale_to(self, image_src, image_dest, width, height, w, h):
        try:
            self.clip_scale_to(image_src, image_dest, width, height, "center", 0 - w / 8, 0 - h / 8, w - w / 4, h - h / 4)
        except IOError:
            self.logger.error("%s clip_north_west_75_percent_scale_to_800x800 error!" % image_src)

    # 从右下角截取四分之三，缩放至800x800
    def clip_south_east_75_percent_scale_to(self, image_src, image_dest, width, height, w, h):
        try:
            self.clip_scale_to(image_src, image_dest, width, height, "center", w / 8, h / 8, w - w / 4, h - h / 4)
        except IOError:
            self.logger.error("%s clip_south_east_75_percent_scale_to_800x800 error!" % image_src)

    # 截取左侧或者上侧两个正方形（以较短边为边长），缩放至800x800
    def clip_west_or_north_scale_to(self, image_src, image_dest, width, height, w, h):
        try:
            # 宽大于高
            if w > h:
                if h > (w / 2):
                    clip_width = w / 2
                    clip_height = w / 2
                    x = 0
                    y = (h - w / 2) / 2
                else:
                    clip_width = h
                    clip_height = h
                    x = (w / 2 - h) / 2
                    y = 0
            # 高大于等于宽
            else:
                if w > (h / 2):
                    clip_width = h / 2
                    clip_height = h / 2
                    x = (w - h / 2) / 2
                    y = 0
                else:
                    clip_width = w
                    clip_height = w
                    x = 0
                    y = (h / 2 - w) / 2

            self.clip_scale_to(image_src, image_dest, width, height, "NorthWest", x, y, clip_width, clip_height)
        except IOError:
            self.logger.error("%s clip_west_or_north_scale_to_800x800 error!" % image_src)

    # 截取右侧下侧两个正方形（以较短边为边长），缩放至800x800
    def clip_east_or_south_scale_to(self, image_src, image_dest, width, height, w, h):
        try:
            if w > h:
                if h > (w / 2):
                    clip_width = w / 2
                    clip_height = w / 2
                    x = w - clip_width
                    y = (h - w / 2) / 2
                else:
                    clip_width = h
                    clip_height = h
                    x = ((w / 2 - h) + w) / 2
                    y = 0
            else:
                if w > (h / 2):
                    clip_width = h / 2
                    clip_height = h / 2
                    x = (w - h / 2) / 2
                    y = clip_height
                else:
                    clip_width = w
                    clip_height = w
                    x = 0
                    y = ((h / 2 - w) + h) / 2

            self.clip_scale_to(image_src, image_dest, width, height, "NorthWest", x, y, clip_width, clip_height)
        except IOError:
            self.logger.error("%s clip_east_or_south_scale_to_800x800 error!" % image_src)

    # 提供处理后的 n 张图片
    def provide_n_images(self, image_src, n):
        if n <= 0:
            return
        if image_src is None:
            self.logger.error("image_src is None!")
            return

        if not os.path.exists(image_src):
            self.logger.error("%s does not exist!" % image_src)
            return
        w, h = map(lambda x:int(x), self.size_pattern.search(os.popen("identify %s"%image_src).read()).groups())
        for i in range(n):
            self.image_funcs[i](image_src, image_src[:image_src.find('.')] + '_800_' + str(i + 1) + '.jpg', 800, 800, w, h)
            self.image_funcs[i](image_src, image_src[:image_src.find('.')] + '_150_' + str(i + 1) + '.jpg', 150, 150, w, h)


    def convert_to(self, image_src, image_dest, dest_width, dest_height):
        if os.path.exists(image_dest):
            self.logger.debug("%s is already exist." % image_dest)
        else:
            cmd = 'convert {0} -thumbnail "{2}x{3}" -background white -gravity center -extent {2}x{3} {1}'.format(
                image_src, image_dest, dest_width, dest_height)
            p = subprocess.Popen(cmd, shell=True)
            _type = "error" if p.wait() else "debug"
            stream = p.stderr if p.wait() else p.stdout
            getattr(self.logger, _type )("%s cmd:%s" % (stream.read() if stream else "", cmd))

    # 裁剪并缩放
    def clip_scale_to(self, image_src, image_dest, dest_width, dest_height, origin, x, y, clip_width, clip_height):
        if os.path.exists(image_dest):
            self.logger.debug("%s is already exists." % image_dest)
        else:
            cmd = 'convert {0}  -gravity {4} -crop {7}x{8}{5:+d}{6:+d} -resize {2}x{3} -extent {2}x{3} {1}'.format(
                image_src, image_dest, dest_width, dest_height, origin, x, y, clip_width, clip_height)
            p = subprocess.Popen(cmd, shell=True)
            _type = "error" if p.wait() else "debug"
            stream = p.stderr if p.wait() else p.stdout
            getattr(self.logger, _type)("%s cmd:%s" % (stream.read() if stream else "", cmd))

    def _process_one_color_images_amazon(self, images, one_color_images):
        same_color_images_count = 0
        for variant_item in one_color_images:
            image_variant_main_file_name = ''
            if variant_item['variant'] == 'MAIN':
                if 'hiRes' in variant_item and variant_item['hiRes'] is not None:
                    image_variant_main_file_name = self.get_image_local_abs_path(images, variant_item['hiRes'])
                elif 'large' in variant_item and variant_item['large'] is not None:
                    image_variant_main_file_name = self.get_image_local_abs_path(images, variant_item['large'])

            if 'hiRes' in variant_item and variant_item['hiRes'] is not None:
                image_hiRes_file_name = self.get_image_local_abs_path(images, variant_item['hiRes'])
                if os.path.exists(image_hiRes_file_name):
                    self.convert_to_800x800_and_640x640_and_150x150(image_hiRes_file_name)
                    same_color_images_count += 1

            elif 'large' in variant_item and variant_item['large'] is not None:
                image_large_file_name = self.get_image_local_abs_path(images, variant_item['large'])
                if os.path.exists(image_large_file_name):
                    self.convert_to_800x800_and_640x640_and_150x150(image_large_file_name)
                    same_color_images_count += 1
            if os.path.exists(image_variant_main_file_name):
                self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)

    def _process_one_color_images_eastbay(self, images, one_color_images):
        same_color_images_count = 0
        for one_position_image in one_color_images:
            image_file_name =self.get_image_local_abs_path(images, one_position_image)
            if os.path.exists(image_file_name):
                self.convert_to_800x800_and_640x640_and_150x150(image_file_name)

            same_color_images_count += 1
        # 主图
        main_image_url = one_color_images[0]
        for i in one_color_images:
            if "_fr_" in i:
                main_image_url = i
                break
        image_variant_main_file_name = self.get_image_local_abs_path(images, main_image_url)
        self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)

    def _process_one_color_images_zappos(self, images, one_color_images):
        same_color_images_count = 0
        for one_position_image in one_color_images:
            image_file_name = self.get_image_local_abs_path(images, one_position_image)
            if image_file_name is None:
                break
            if os.path.exists(image_file_name):
                self.convert_to_800x800_and_640x640_and_150x150(image_file_name)

            same_color_images_count += 1
        # 主图
        main_image_url = one_color_images[0]
        for i in one_color_images:
            if "-p-" in i:
                main_image_url = i
                break
        image_variant_main_file_name = self.get_image_local_abs_path(images, main_image_url)
        self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)

    def _process_color_images_amazons(self, document):
        images = document['images']
        color_images = json.loads(document['color_images'])

        # 只有初始的一种颜色的图片
        if 'initial' in color_images.keys():
            initial = color_images['initial']
            self._process_one_color_images_amazon(images, initial)
        # 处理每种颜色
        else:
            for one_color_images in color_images:
                self._process_one_color_images_amazon(images, color_images[one_color_images])
        return True

    def _process_color_images_backcountrys(self, document):
        images = document['images']
        color_images = {}
        map(lambda x:color_images.setdefault(re.search(r"/([^/_]+)[^/]*?\.jpg", x["url"]).group(1), []).append(x), images)
        # 处理每种颜色
        for color, one_color_images in color_images.items():
            self._process_one_color_images_backcountrys(one_color_images)
        return True

    def _process_one_color_images_backcountrys(self, one_color_images):
        same_color_images_count = 0
        find_images = []
        for image in one_color_images:
            if os.path.exists(image["path"]):
                find_images.append(image)
                self.convert_to_800x800_and_640x640_and_150x150(image["path"])
                same_color_images_count += 1

        if find_images:
            image_variant_main_file_name = find_images[0]["path"]
            self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)
        else:
            self.logger.info("no images found")

    def _process_color_images_ralphlaurens(self, document):
        images = document['images']
        color_map = json.loads(document.get('color_map', "[]"))

        for color in color_map.values():
            self._process_one_color_images_ralphlaurens(color, images)
        return True

    def _process_one_color_images_ralphlaurens(self, color, images):
        regx = re.complie(color)
        find_images = []
        same_color_images_count = 0
        for image in images:
            if regx.search(image["url"]):
                if os.path.exists(image["path"]):
                    find_images.append(image)
                    self.convert_to_800x800_and_640x640_and_150x150(image["path"])
                    same_color_images_count += 1

                    # 主图
        if find_images:
            image_variant_main_file_name = find_images[0]["path"]
            self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)
        else:
            self.logger.info("no images found")

    def _process_color_images_eastbays(self, document):
        images = document['images']
        color_images = document['sku_images']
        for one_color_images in color_images:
            self._process_one_color_images_eastbay(images, color_images[one_color_images])
        return True

    def _process_color_images_zapposs(self, document):
        images = document['images']
        color_images = document['color_images']
        colorIds = document['colorIds']
        for colorId in colorIds:
            one_color_images = []
            for one_image in color_images:
                if one_image[0] == colorId:
                    one_color_images.append(one_image[2])
                    self._process_one_color_images_zappos(images, one_color_images)
        return True

    _process_color_images_6pms = _process_color_images_zapposs

    def _process_color_images_finishlines(self, document):
        same_color_images_count = 0
        images = document['images']
        one_color_images = document['image_urls']
        for one_image in one_color_images:
            image_file_name = self.get_image_local_abs_path(images, one_image)
            if os.path.exists(image_file_name):
                self.convert_to_800x800_and_640x640_and_150x150(image_file_name)
            same_color_images_count += 1
        main_image_url = one_color_images[0]
        for i in one_color_images:
            if "_fr" in i:
                main_image_url = i
                break
        image_variant_main_file_name = self.get_image_local_abs_path(images, main_image_url)
        self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)
        return True

    def _process_color_images_ashfords(self, document):
        same_color_images_count = 0
        images = document['images']
        one_color_images = document['image_urls']
        for one_image in one_color_images:
            image_file_name = self.get_image_local_abs_path(images, one_image)
            if os.path.exists(image_file_name):
                self.convert_to_800x800_and_640x640_and_150x150(image_file_name)
            same_color_images_count += 1

        main_image_url = one_color_images[0]
        for i in one_color_images:
            if "_FXA" in i:
                main_image_url = i
                break
        image_variant_main_file_name = self.get_image_local_abs_path(images, main_image_url)
        self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)
        return True

    def _process_color_images_only_image_urls(self, document):
        same_color_images_count = 0
        images = document['images']
        color_images = document['image_urls']
        for one_image in color_images:
            image_file_name = self.get_image_local_abs_path(images, one_image)
            if os.path.exists(image_file_name):
                self.convert_to_800x800_and_640x640_and_150x150(image_file_name)
                same_color_images_count += 1
        for main_image_url in color_images:
            image_variant_main_file_name = self.get_image_local_abs_path(images, main_image_url)
            if os.path.exists(image_variant_main_file_name):
                self.provide_n_images(image_variant_main_file_name, self.g_requre_images_count - same_color_images_count)
                break
        return True

    def _process_color_images_rakutens(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_drugstores(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_vitaminworlds(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_jomashops(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_watchismos(self, document):
        return self. _process_color_images_only_image_urls(document)

    def _process_color_images_jacobtimes(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_thewatcherys(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_watchcos(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_blueflys(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_jimmyjazzs(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_noblecollections(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_neimanmarcuss(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_pyss(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_worldofwatchess(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_titleboxings(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_onlineshoess(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_macyss(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_7forallmankindss(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_asoss(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_aes(self, document):
        return self._process_color_images_only_image_urls(document)

    def _process_color_images_neweggs(self, document):
        return self._process_color_images_only_image_urls(document)

