import os
import copy
import yaml
import requests

from pylib.log import log
from pylib.request import request


class NacosApi:
    server_url = os.getenv("nacos-api.server_url", '').removesuffix('/').removesuffix('/nacos/v3') + '/nacos/v3'  # 8848
    console_url = os.getenv("nacos-api.console_url", '').removesuffix('/').removesuffix('/v3/console') + '/v3/console'    # 8080
    username = os.getenv("nacos-api.username", "nacos")
    password = os.getenv("nacos-api.password", "nacos")
    access_token = None

    def __init__(self, params: dict = None):
        """初始化Nacos API
        :Params params.server_url: 服务地址
        :Params params.console_url: 控制台地址
        :Params params.username: 用户名
        :Params params.password: 用户密码"""
        params = params or {}
        self.server_url = params.get('server_url', self.server_url)
        self.console_url = params.get('console_url', self.console_url)
        self.username = params.get('username', self.username)
        self.password = params.get('password', self.password)
        self.login()

    @classmethod
    def heartbeat(cls):
        """检查Nacos是否存活"""
        response = requests.get(f"{cls.console_url}/{'health/liveness'}", timeout=5)
        return response.status_code == 200 and response.json().get('code') == 0

    def login(self) -> str:
        """登录Nacos"""
        url = f"{self.server_url}/auth/user/login"
        data = {"username": self.username, "password": self.password}
        response = request.post(url, data=data)
        log.warning('Nacos登录结果', response.status_code, response.text)
        self.access_token = response.json()['accessToken']
        return self.access_token

    @staticmethod
    def _read_content(data: dict) -> dict:
        """根据数据类型解析读取"""
        content = data['content']
        if data['type'] == 'yaml':
            content = yaml.load(content, Loader=yaml.FullLoader)
        return content

    def get_config(self, params: dict = None):
        """获取配置"""
        params = params or {}
        url = f"{self.console_url}/cs/config"
        params = copy.deepcopy({**{
            'namespaceId': 'public',
            'groupName': 'DEFAULT_GROUP',
            'dataId': 'Config'
        }, **params})
        params = copy.deepcopy(params or {})
        params['accessToken'] = params.get('accessToken', self.access_token)
        data = requests.get(url, params=params).json()['data']
        return data and self._read_content(data) or {}
