import os

from pylib.log import log
from pylib.api.feishu_api import FeishuApi
from pylib.api.gitlab_api import GitlabApi


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
        projects = [580, 495, 1500, 582, 491, 2713, 1671, 2353, 1520, 493, ]
        for project in projects:
            # rst = GitlabApi.add_project_member(project, 860, 30)
            rst = GitlabApi.add_project_member(project, 639, 30)
            print(rst.status_code, rst.text)
            break


if __name__ == "__main__":
    Main().run()
