import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from PIL import Image
from io import BytesIO
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tenacity import retry, stop_after_attempt, wait_fixed
import argparse


SCROLL_PAUSE_TIME = 1
SEARCH_PAUSE_TIME = 20
DOWNLOAD_PAUSE_TIME = 0.5


def get_image_urls_from_search(keyword, num_images, headless=False):
    # Initialize a Chrome browser in headless mode
    # Setting up Chrome options
    opts = Options()
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.")
    if headless:
        opts.add_argument("--headless")
    browser = webdriver.Chrome(options=opts)
    browser.get('https://www.amazon.com')

    search_box = WebDriverWait(browser, SEARCH_PAUSE_TIME).until(
        EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
    )
    search_box.clear()
    search_box.send_keys(keyword)
    search_box.submit()

    # Scroll page to make sure all the images are loaded
    last_height = browser.execute_script("return document.body.scrollHeight")  # Get scroll height

    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # Scroll down to bottom
        time.sleep(SCROLL_PAUSE_TIME)  # Wait to load page

        # Calculate new scroll height and compare with last scroll height
        new_height = browser.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    images = browser.find_elements(By.CSS_SELECTOR, "img.s-image")
    print(f'retrieved {len(images)} images')

    image_urls = []
    count = 0
    for image in images:
        # Find and save the large image
        try:
            large_image_url = image.get_attribute('srcset').split(' ')[-2]
            #print(large_image_url)
        except:
            continue
        image_urls.append(large_image_url)
        count += 1
        print(f'scraped {count}/{num_images} images')
        if count == num_images:
            break

    browser.quit()

    return image_urls


def download_images(urls, dest='images'):

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(DOWNLOAD_PAUSE_TIME))
    def download_and_save_image(url, image_path, headers):
        response = requests.get(url, headers=headers)
        img = Image.open(BytesIO(response.content))
        img.save(image_path)

    os.makedirs(dest, exist_ok=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    for i, url in enumerate(urls, 1):
        time.sleep(DOWNLOAD_PAUSE_TIME)
        image_path = f'{dest}/product{i}.jpg'
        download_and_save_image(url, image_path, headers)
        print(f'Saved image {i}')


# Define command line arguments
parser = argparse.ArgumentParser(description='Web scrape product images from Amazon.')
parser.add_argument('keyword', type=str, help='The search term to use on Amazon.')
parser.add_argument('num_images', type=int, default=15, help='The number of images to scrape.')
args = parser.parse_args()

image_urls = get_image_urls_from_search(args.keyword, args.num_images)
dest = f'images/{args.keyword}'.replace(' ', '_')
print(image_urls)
download_images(image_urls, dest)
print(f'images saved to {dest}')
