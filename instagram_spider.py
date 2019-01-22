# coding=utf-8

import requests
import json
import re
import os
from hashlib import md5


headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
    "cookie": '',  # 换成你自己的cookie
}

url = "https://www.instagram.com/graphql/query/?"


def get__html(url):  # 获取网页HTML
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print('请求网页源代码错误, 错误状态码：', response.status_code)
    except Exception as e:
        print(e)
        return None


def get_query_hash():  # 获取query_hash参数
    url = 'https://www.instagram.com/static/bundles/metro/ProfilePageContainer.js/b5e793e9399f.js'
    html = get__html(url)
    query_hash = re.findall(r'queryId\:\"(.*?)\"\,', html, re.S)[2]
    print("query_hash:", query_hash)
    return query_hash


def get_json(html):  # 解析json
    user_id = re.findall('"profilePage_([0-9]+)"', html, re.S)[0]  # 获取博主id
    res = re.search(r'window._sharedData = (.*?);', html).group(1)
    json_content = json.loads(res)
    edges = json_content['entry_data']['ProfilePage'][0]['graphql']['user']["edge_owner_to_timeline_media"]["edges"]
    page_info = json_content["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]['page_info']
    cursor = page_info['end_cursor']  # 下页的指标参数
    next_page = page_info['has_next_page']  # 判断是否有下页
    urls = []
    for edge in edges:
        if edge['node']['display_url']:
            display_url = edge['node']['display_url']
            urls.append(display_url)
    return urls, user_id, cursor, next_page


def get_next_img(query_hash, user_id, cursor, next_page):  # 解析下一页获取url
    while next_page:  # 判断是否有下一页
        params = {
            "query_hash": "{}".format(query_hash),
            "variables": '{{"id":"{0}","first":12,"after":"{1}"}}'.format(user_id, cursor)
        # 大括号是特殊转义字符，如果需要原始的大括号,用{{代替{
        }
        res = requests.get(url, params=params, headers=headers)
        json_content = json.loads(res.text)
        edges = json_content['data']['user']['edge_owner_to_timeline_media']['edges']
        cursor = json_content['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
        next_page = json_content['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
        urls = []
        for info in edges:
            if info['node']['is_video']:  # 判断是否是视频
                video_url = info['node']['video_url']
                if video_url:
                    urls.append(video_url)
            else:
                if info['node']['display_url']:
                    display_url = info['node']['display_url']
                    urls.append(display_url)
        yield urls
    print("没有下一页了")


def get_content(url):  # 下载图片
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print('请求照片二进制流错误, 错误状态码：', response.status_code)
    except Exception as e:
        print(e)
        return None


def save_content(url, blogger_name):  # 下载图片保存到本地
    for info in url:
        url_type = re.search(r'(.*?)\?.*', info).group(1)[-3:]  # 获取文件后缀名
        url_html = get_content(info)  # 下载的二进制
        img_path = blogger_name + os.path.sep   # 保存文件夹名称为博主名字
        if not os.path.exists(img_path):
            os.makedirs(img_path)
        file_path = img_path + os.path.sep + '{0}.{1}'.format(md5(url_html).hexdigest(), url_type)  # md5加密，图片去重
        print("储存到本地：" + file_path)
        if not os.path.exists(file_path):
            with open(file_path, 'wb') as f:
                f.write(url_html)
                f.close()


def main(blogger_name):
    uri = "https://www.instagram.com/{}/".format(blogger_name)
    html = get__html(uri)  # 输入博主名称,获取博主首页HTML
    query_hash = get_query_hash()  # 获取query_hash参数
    urls, user_id, cursor, next_page = get_json(html)  # 获取下一页参数，和第一页的图片url
    save_content(urls, blogger_name)  # 保存到第一页到本地
    url_list = get_next_img(query_hash, user_id, cursor, next_page)  # 循环获取每页图片url
    for url in url_list:
        save_content(url, blogger_name)  # 保存到本地


if __name__ == '__main__':
    blogger_name = str(input("请输入博主名称："))
    main(blogger_name)
