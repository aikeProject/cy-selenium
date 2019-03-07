import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
import pymongo
from config import *

# 链接数据库MongoDB
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

# 使用chrome浏览器
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
browser = webdriver.Chrome(chrome_options=chrome_options)
wait = WebDriverWait(browser, 10)

# 已经过时
# browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)
# wait = WebDriverWait(browser, 10)

# 搜索
def search():
    print('正在搜索...')
    try:
        browser.get('https://www.taobao.com')
        # presence_of_element_located 已经加载好了
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#q'))
        )
        # element_to_be_clickable 可点击
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )
        # send_keys 输入
        input.send_keys(KEYWORD)
        # 点击搜索
        submit.click()
        # 获取总页数
        total = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'
            ))
        )
        # 加载第一页商品
        get_products()
        return total.text
    except TimeoutException:
        # 递归调用 search 
        return search()

# 翻页
def next_page(page_n):
    print('正在翻页...', page_n)
    try:
        # 输入页码的输入框
        input = wait.until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > input'
            ))
        )
        # 翻页按钮
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
        )
        input.clear()
        input.send_keys(page_n)
        submit.click()
        # 检查是否是当前分页
        wait.until(
            EC.text_to_be_present_in_element((
                By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'
            ), str(page_n))
        )
        # 获取商品
        get_products()
    except TimeoutException:
        next_page(page_n)

# 获取商品信息
def get_products():
    # 等待商品列表加载完毕
    wait.until(EC.presence_of_element_located((
        By.CSS_SELECTOR, '#mainsrp-itemlist .items .item'
    )))
    # 获取网页源代码
    html = browser.page_source
    dom = pq(html)
    items = dom('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'images': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text(),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }
        # print('product: ', product)
        save_to_mongo(result=product)

def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储在MongoDB成功...')
    except Exception:
        print('存储MongoDB错误....')    

def main():
    try:
        total = search()
        total = int(re.compile('(\d+)').search(total).group(1))
        # total = 5
        print('总分页数：', total)
        for i in range(2, total + 1):
            next_page(i)
    except Exception:
        print('出错了...')
    finally:
        browser.close()

if __name__ == "__main__":
    main()