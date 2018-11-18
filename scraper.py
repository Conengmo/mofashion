"""

https://selenium-python.readthedocs.io/api.html#module-selenium.webdriver.remote.webelement
"""

import os
import uuid
import contextlib
from typing import List, Optional

from selenium import webdriver
import requests


PATH = r'F:\mofashion-data'


@contextlib.contextmanager
def yield_driver():
    driver = None
    try:
        driver = webdriver.Firefox()
        driver.implicitly_wait(3)
        driver.maximize_window()  # images are larger this way on some sites
        yield driver
    finally:
        if driver is not None:
            driver.quit()


class ImageDownloader:

    def __init__(self, run_name):
        self.run_name = run_name
        self.path = self.get_path(run_name)

    @staticmethod
    def get_path(run_name: str):
        path = os.path.join(PATH, run_name)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def download_image_elements(self, images: list):
        for item in images:
            height = item.size['height']
            width = item.size['width']
            if height < 100 or width < 100:
                continue
            src = item.get_property('src')
            self.download_image(src)

    def download_image(self,
                       image_url: str,
                       image_id: Optional[str] = None,
                       empty_image: Optional[bytes] = None):
        resp = requests.get(image_url)
        resp.raise_for_status()
        file_type, extension = resp.headers['Content-Type'].split('/')
        assert file_type == 'image'
        assert extension in ('jpeg',)
        if empty_image is not None:
            if empty_image == resp.content:
                return
        if image_id is None:
            image_id = uuid.uuid4()
        filepath = os.path.join(self.path, f'{self.run_name}_{image_id}.{extension}')
        with open(filepath, 'wb') as f:
            f.write(resp.content)


def main_hm(gender: str):
    size = 12
    if gender == 'f':
        url = ('https://www2.hm.com/nl_nl/dames/shop-by-product/view-all.html?sort=stock'
               '&productTypes=blouse,broek,colbert,gilet,jas,jeans,jumpsuit,jurk,legging,'
               'ochtendjas,overhemd,poncho,rok,short,sweater,t-shirt,top,trui,tuniek,vest'
               '&image-size=small&image={}&offset={}&page-size={}')
    elif gender == 'm':
        url = ('https://www2.hm.com/nl_nl/heren/shop-op-item/view-all.html?sort=stock'
               '&productTypes=broek,colbert,gilet,jack,jas,jeans,legging,longjohns,overhemd,'
               'short,sweater,t-shirt,top,trui,vest'
               '&image-size=small&image={}&offset={}&page-size={}')
    else:
        raise ValueError('gender argument may be either \'m\' or \'f\'.')
    downloader_models = ImageDownloader(f'hm-{gender}-models')
    downloader_items = ImageDownloader(f'hm-{gender}-items')
    with yield_driver() as driver:
        driver.get(url.format('model', 0, 12))
        item = driver.find_element_by_class_name('load-more-heading')
        available = int(item.get_attribute('data-total'))
        for offset in range(0, available, size):
            print(f'Working on {offset} to {offset + size} of {available}.')
            for img_type in ('model', 'stillLife'):
                driver.get(url.format(img_type, offset, size))
                images = driver.find_elements_by_class_name('item-image')
                images_models = [item for item in images
                                 if 'LOOKBOOK' in item.get_property('src')]
                images_items = [item for item in images
                                if 'DESCRIPTIVESTILLLIFE' in item.get_property('src')]
                images_failed = [item for item in images
                                 if item not in images_models and item not in images_items]
                if images_failed:
                    print(f'{len(images_failed)} failed images')
                downloader_models.download_image_elements(images_models)
                downloader_items.download_image_elements(images_items)


def main_uniqlo(gender: str):
    size = 24
    if gender == 'm':
        url = ('https://www.uniqlo.com/eu/en/men?prefn1=category-id&sz={size}&start={offset}'
               '&format=page-element&prefv1=IDm-tops|IDm-bottoms|IDm-knitwear|IDm-outerwear')
    elif gender == 'f':
        url = ('https://www.uniqlo.com/eu/en/women?prefn1=category-id&sz={size}&start={offset}'
               '&format=page-element&prefv1=IDw-outerwear|IDw-knitwear|IDw-tops|IDw-bottoms')
    else:
        raise ValueError('gender argument may be either \'m\' or \'f\'.')
    url_image = 'https://uniqlo.scene7.com/is/image/UNIQLO/goods_{product_id}_sub{sub}?$pdp-medium$'

    dl_models_full = ImageDownloader(f'un-{gender}-models-full')
    dl_models_partial = ImageDownloader(f'un-{gender}-models-partial')
    dl_items_partial = ImageDownloader(f'un-{gender}-items-partial')

    resp = requests.get('https://uniqlo.scene7.com/is/image/UNIQLO/goods_411924_sub2?$pdp-medium$')
    resp.raise_for_status()
    empty_image = resp.content

    product_ids: List[int] = []

    with yield_driver() as driver:
        for offset in range(0, 10000, size):
            print(f'Working on {offset} to {offset + size}.')
            driver.get(url.format(size=size, offset=offset))
            for item in driver.find_elements_by_class_name('productTile__link'):
                product_url = item.get_attribute('href')
                product_id = int(product_url.rstrip('.html').split('-')[-1])
                if product_id in product_ids:
                    continue
                for i in range(1, 4):
                    dl_models_full.download_image(url_image.format(product_id=product_id, sub=i),
                                                  image_id=f'{product_id}_{i}',
                                                  empty_image=empty_image)
                dl_models_partial.download_image(url_image.format(product_id=product_id, sub=4),
                                                 image_id=f'{product_id}_{i}',
                                                 empty_image=empty_image)
                for i in range(5, 8):
                    dl_items_partial.download_image(url_image.format(product_id=product_id, sub=i),
                                                    image_id=f'{product_id}_{i}',
                                                    empty_image=empty_image)
                product_ids.append(product_id)


# def main_zalando():
#     available = 892
#     # done until page 45
#     url = 'https://www.zalando.nl/dameskleding/?p={}'
#     with yield_driver() as driver:
#         for page in range(2, available):
#             print(f'Working on page {page} of {available}.')
#             driver.get(url.format(page))
#             images = driver.find_elements_by_class_name('cat_image-1byrW')
#             print(f'Found {len(images)} images.')
#             download_image_elements(images, 'za-f-a')


if __name__ == '__main__':
    # main_hm(gender='m')
    # main_hm(gender='f')
    main_uniqlo(gender='m')
    main_uniqlo(gender='f')
    # main_zalando()
