from pylib.decorator.decorator import Decorator as _Decorator

import time
import functools

from collections import deque
from collections import defaultdict

from pylib.log import log


class TimeitDecorator(_Decorator):
    """
    添加方法装饰器
        使用方法：
            无参注解：@TimeitDecorator
            有参注解：@TimeitDecorator()
    注意：
        若同时使用@staticmethod注解
        或用@classmethod注解，它们应当先于@TimeitDecorator注解
    """
    _elapsed_time = defaultdict(lambda: deque(maxlen=1))

    def __init__(self, *args, **kwargs):
        super(TimeitDecorator, self).__init__(*args, **kwargs)

    def _get_wrapper(self, instance=None, owner=None):
        """获取装饰器函数"""
        @functools.wraps(self.callable_obj)
        def wrapper(*args, **kwargs):
            start_time = time.time()    # 计时开始
            key = self._get_key(instance, owner, *args, **kwargs)   # 获取注解key
            # 进行Key的转化；因为注解Key过长，如：Callback.temp.0xffffa3744790(func_id)，格式也不符合topic
            # 取方法名作为key值
            key = key.split('.')
            key = '/'.join(key[-3:-1] or key)

            try:    # 运行被注解的方法
                args = (instance,) + args if instance is not None else args     # 实例方法时，要将实例插入元组args首位
                return self.callable_obj(*args, **kwargs)
            finally:    # 计时结束
                TimeitDecorator._elapsed_time[key].append(time.time() - start_time)
                # log.debug('TimeitDecorator._elapsed_time',
                #           {k: round(v[0] * 1000, 3) for k, v in dict(TimeitDecorator._elapsed_time).items()})
                value = 1000 * sum(TimeitDecorator._elapsed_time[key]) / (
                        float(len(TimeitDecorator._elapsed_time[key])) or 1)
                log.debug('_elapsed_time', key, f"{round(value, 3)}ms", silence=value < 500, index=1)
        return wrapper
