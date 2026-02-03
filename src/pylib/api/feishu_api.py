import re
import os
import json

from pylib.log import log
from pylib.request import request


class FeishuApi:
    """飞书API"""
    robot_url = os.getenv('feishu-api.robot.standard.url')
    headers = {
        "Content-Type": "application/json; charset=utf-8"
    }

    @staticmethod
    def _get_card_text_data(title, msg):
        """获取卡片格式发送数据"""
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "content": title,
                        "tag": "plain_text"
                    }
                },
                "elements": [{
                    "tag": "div",
                    "text": {
                        "content": msg,
                        "tag": "lark_md"
                    }
                }]
            }
        }

    @staticmethod
    def _get_post_text_data(title, msg):
        """获取Post格式发送数据"""
        msg = re.sub(r'(?<![*])[*]{2}(.+?)[*]{2}(?![*])(?![*])', r'\1', msg)    # 将加粗的内容还原
        data = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [
                            [{
                                "tag": "text",
                                "text": f"{msg}"
                            }]
                        ]
                    }
                }
            }
        }

        # 将文本中MD超链接的部分转为飞书格式（此步骤可省略）
        content = []
        md_href = r'(\[.+?]\(.+?\))'
        msgs = re.split(md_href, msg)
        for msg in msgs:
            if re.fullmatch(md_href, msg):
                # 将匹配到的MD超链接文本按文本和超链接分割开，按飞书格式放入字典中
                content.append({
                    "tag": "a",
                    "text": ''.join(re.findall(r'\[(.+?)]', msg)),
                    "href": ''.join(re.findall(r'\((.+?)\)', msg))
                })
            else:
                content.append({
                    "tag": "text",
                    "text": msg
                })
        data['content']['post']['zh_cn']['content'] = [content]

        return data

    @classmethod
    def send(cls, msg, title='', url='', msg_type='post'):
        """向飞书发送通知
        :Params msg: 发送的文本，以Markdown格式传入
        :Params url: 详情链接
        :Params title: 消息标题
        """
        # 0. 参数准备
        url = url or cls.robot_url     # 选择发向哪个机器人

        # 1. 发送消息
        data = {"msg_type": "text", "content": {"text": msg}}
        if msg_type == 'post':
            data = cls._get_post_text_data(title, msg)
        response = request.post(url, headers=cls.headers, data=json.dumps(data))
        log.info('飞书消息通知结果', response.status_code, response.text)
        return response.json()
