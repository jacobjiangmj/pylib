# -*- coding:utf-8 -*-
import copy


class CallbackDict(dict):
    """可回调（被监听）的字典，当字典中的值发生变化时，会调用callback函数"""
    callback = None

    def __init__(self, callback=None, default_dict=None):
        super(CallbackDict, self).__init__(default_dict or {})
        self.callback = callback

    def __setitem__(self, key, value):
        old_value = self.get(key)
        if old_value != value:
            super(CallbackDict, self).__setitem__(key, value)
            self.callback(self, key=key, value=value, old_value=old_value)

    def __delitem__(self, key):
        super(CallbackDict, self).__delitem__(key)

    def update(self, *args, **kwargs):
        """覆写父类的 update 方法，使得在调用 update 方法时，也会调用 callback 函数"""
        for key, value in dict(*args, **kwargs).items():
            self[key] = value  # 利用已经覆写的 __setitem__ 方法，检测值是否发生变化来调用callback

    def setdict(self, key, value):
        """处理第二级字典的回调"""
        self.setdefault(key, {})
        old_value = copy.deepcopy(self[key])
        old_value.update(value)
        self[key] = old_value
