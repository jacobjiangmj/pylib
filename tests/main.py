import time

from pylib.api.feishu_api import FeishuApi


class Main:
    @staticmethod
    def _func(*args):
        time.sleep(1)
        return args

    @staticmethod
    def run():
        last_notify, notify_interval = 0, 6 * 3600
        if time.time() - last_notify > notify_interval:
            FeishuApi.send('告警通知应用无心跳', url='https://open.feishu.cn/open-apis/bot/v2/hook/609f3a61-70d5-4fe1-a627-593d3b30808c')


if __name__ == "__main__":
    Main().run()
