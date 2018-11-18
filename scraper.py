"""Script to scrape images from HM, Uniqlo and Mango websites.

Uses Selenium with Firefox webdriver.

https://selenium-python.readthedocs.io/api.html#module-selenium.webdriver.remote.webelement
"""

import os
import uuid
import contextlib
from typing import List, Optional
import time

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
                       empty_image: Optional[bytes] = None,
                       raise_exc: bool = True):
        if image_id is None:
            image_id = uuid.uuid4()
        filepath = os.path.join(self.path, f'{self.run_name}_{image_id}.jpeg')
        if os.path.exists(filepath):
            return
        resp = requests.get(image_url)
        if resp.status_code != 200:
            if not raise_exc:
                return
            resp.raise_for_status()
        file_type, extension = resp.headers['Content-Type'].split('/')
        if file_type != 'image' or extension != 'jpeg':
            if not raise_exc:
                return
            raise ValueError('Image HTTP headers have unexpected content type.')
        if empty_image is not None:
            if empty_image == resp.content:
                return
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


def main_mango(gender: str):
    # This function is slow... it's needlessly iteration.
    if gender == 'm':
        base_url = 'https://shop.mango.com/nl/heren/'
        url_suffixs = ['t-shirts_c12018147', 'jassen_c32859776', 'jasjes_c16042202',
                       'blazers_c14858698', 'truien-en-vesten_c12660076', 'sweaters_c71156082',
                       'overhemden_c10863844', 'broeken_c11949748', 'jeans_c23998484']
    elif gender == 'f':
        base_url = 'https://shop.mango.com/nl/dames/'
        url_suffixs = ['vesten-en-truien_c18200786', 'jassen_c67886633', 'jasjes_c69427016',
                       'jurken_c55363448', 'jumpsuits_c99834840', 'blouses_c78920337',
                       't-shirts-en-tops_c66796663',  'broeken_c52748027', 'jeans_c99220156',
                       'rokken_c20673898']
    else:
        raise ValueError('gender argument may be either \'m\' or \'f\'.')
    url_image = ('https://st.mngbcn.com/rcs/pics/static/T3/fotos/S20/'
                 '{product_id}_{c_code}{suffix}.jpg?ts={timestamp}&imwidth=427&imdensity=1')

    dl_models_full = ImageDownloader(f'ma-{gender}-models-full')
    dl_models_partial = ImageDownloader(f'ma-{gender}-models-partial')
    dl_items_full = ImageDownloader(f'ma-{gender}-items-full')

    with yield_driver() as driver:
        for url_suffix in url_suffixs:
            full_urls = set()
            driver.get(base_url + url_suffix)
            time.sleep(2)
            driver.find_element_by_id('navColumns4').click()
            time.sleep(2)
            while True:
                time.sleep(2)
                item_urls = [item.get_attribute('src')
                             for item in driver.find_elements_by_class_name('product-list-image')]
                print(f'{url_suffix}: got {len(item_urls)} elements, total is {len(full_urls)}.')
                len_full_urls = len(full_urls)
                for item_url_full in item_urls:
                    if item_url_full in full_urls:
                        continue
                    item_url = item_url_full.split('?')[0]
                    if '.gif' in item_url:
                        continue
                    parts_str = item_url.rstrip('.jpg').split('/')[-1]
                    parts = parts_str.split('_')
                    product_id = int(parts[0])
                    c_code = parts[1].split('-')[0]

                    def call_download(dl_, suffix_):
                        dl_.download_image(url_image.format(product_id=product_id, c_code=c_code,
                                                            suffix=suffix_,
                                                            timestamp=int(time.time())),
                                           image_id=f'{product_id}{suffix_}',
                                           raise_exc=False)

                    for suffix in ('', '_R'):
                        call_download(dl_models_full, suffix)
                    for suffix in ('_D1', '_D2'):
                        call_download(dl_models_partial, suffix)
                    call_download(dl_items_full, '_B')
                    full_urls.add(item_url_full)
                    diff = len(full_urls) - len_full_urls
                    if diff > 0 and diff % 4 == 0:
                        driver.execute_script("window.scrollBy(0,600);")
                if len(full_urls) == len_full_urls:
                    print('End of page')
                    break


if __name__ == '__main__':
    # main_hm(gender='m')
    # main_hm(gender='f')  # Ran HM female until 1680
    # main_uniqlo(gender='m')
    # main_uniqlo(gender='f')
    # main_mango(gender='m')
    # main_mango(gender='f')
    print('Finished')
