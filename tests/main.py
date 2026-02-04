import os

from pylib.log import log
from pylib.callback_dict import CallbackDict
from pylib.api.feishu_api import FeishuApi


class Callback:
    feishu_api_robot_monitoring_url = os.getenv('feishu-api.robot.standard.url')

    @classmethod
    def callback(cls, obj, key, value, old_value):
        if key == 'alertmanager-webhook.production':
            if old_value == 1 and value == 0:
                FeishuApi.send(f"告警通知应用无心跳: {key} - {value} ❌", url=cls.feishu_api_robot_monitoring_url)
            elif old_value == 0 and value == 1:
                FeishuApi.send(f"告警通知应用心跳恢复: {key} - {value} ✅", url=cls.feishu_api_robot_monitoring_url)
            log.info(f"{key} - {value} old_value: {old_value}")


class Main:
    @staticmethod
    def _func(*args, **kwargs):
        print(args, kwargs)
        return args

    @staticmethod
    def run():
        a = CallbackDict(Callback.callback)
        a['alertmanager-webhook.production'] = 0
        a['alertmanager-webhook.production'] = 1
        a['alertmanager-webhook.production'] = 0


if __name__ == "__main__":
    Main().run()
