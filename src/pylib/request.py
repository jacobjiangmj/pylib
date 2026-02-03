import re
import requests

from pylib.log import log
from pylib.methods import Methods
from pylib.decorator.time_decorator import TimeitDecorator


class _Request:
    silence_list = ['jobs', 'trace', 'tags', 'nacos/v3/auth/user/login']
    silence_re_list = [r'pipelines/\d+$']

    @classmethod
    def _get_silence(cls, url: str) -> bool:
        return any([
            any([url.rstrip('/').endswith(s) for s in cls.silence_list]),
            any([re.search(pattern, url) for pattern in cls.silence_re_list])
        ])

    @classmethod
    @TimeitDecorator
    def get(cls, url: str, headers: dict = None, params: dict = None, data: dict = None, **kwargs):
        """重新接管HTTP请求，用于打印调试日志"""
        log.debug(
            url,
            'GET',
            'params:',
            params or {},
            'data:', data or {},
            'headers:', headers or {},
            'kwargs:', kwargs,
            Methods.get_stack_funcs(8),
            silence=cls._get_silence(url), index=2)
        return requests.get(url, headers=headers or {}, params=params or {}, **kwargs)

    @classmethod
    @TimeitDecorator
    def post(cls, url: str, headers: dict = None, params: dict = None, data: dict = None, **kwargs):
        """重新接管HTTP请求，用于打印调试日志"""
        log.debug(
            url,
            'POST',
            'headers:', headers or {},
            'params:', params or {},
            'data:', data or {},
            'kwargs:', kwargs,
            silence=cls._get_silence(url), index=1)
        return requests.post(url, headers=headers, params=params or {}, data=data, **kwargs)

    @classmethod
    @TimeitDecorator
    def delete(cls, url: str, headers: dict = None, params: dict = None, data: dict = None, **kwargs):
        """重新接管HTTP请求，用于打印调试日志"""
        log.debug(
            url,
            'DELETE',
            'headers:', headers or {},
            'params:', params or {},
            'data:', data or {},
            'kwargs:', kwargs,
            silence=cls._get_silence(url), index=1)
        return requests.delete(url, headers=headers, params=params or {}, data=data, **kwargs)

request = _Request
