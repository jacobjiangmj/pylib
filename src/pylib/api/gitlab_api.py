import os
import json
import aiohttp
import requests
import urllib.parse

from enum import IntEnum, unique

from pylib.log import log
from pylib.request import request


@unique
class GitlabAccessLevel(IntEnum):
    """Gitlab 访问级别枚举类，对应 Gitlab::Access 模块的权限定义"""
    NO_ACCESS = 0   # 无访问权限
    MINIMAL_ACCESS = 5  # 最小访问权限
    GUEST = 10  # 访客
    PLANNER = 15    # 计划者
    REPORTER = 20   # 报告者
    DEVELOPER = 30  # 开发者
    MAINTAINER = 40     # 维护者
    OWNER = 50  # 拥有者

    def __int__(self):
        """获取整形时，默认返回它的值的整形"""
        return int(self.value)


class GitlabApi:
    url = os.getenv("gitlab-api.url")
    _headers = {
        "PRIVATE-TOKEN": os.getenv('gitlab-api.access_token')
    }
    stop_status = ['success', 'failed', 'canceled', 'skipped', 'manual', 'scheduled']
    failed_status = ['failed', 'canceled', 'skipped', 'manual', 'scheduled']
    running_status = ['created', 'waiting_for_resource', 'preparing', 'pending', 'running']
    params = {
        "per_page": 100
    }

    def heartbeat(self):
        return requests.get(f"{self.url}/projects", timeout=5).status_code == 200

    def _search(self, search, scope='projects'):
        """ The scope to search in. Values include
            projects, issues, merge_requests, milestones, snippet_titles, users,
            blobs, commits, notes, wiki_blobs
        """
        params = {"scope": scope, "search": search}
        response = requests.get(f"{self.url}/search", params=params, headers=self._headers)
        return json.loads(response.text)

    """项目组操作"""
    def _get_group(self, group_name):
        """ 获取项目组
            1. 根据项目组名调用模糊匹配API。（没有完全匹配）
            2. 过滤出项目组名相等的项目，并返回。
            3. 无匹配则返回{}
        """
        for group in self._groups(group_name):
            if group['name'] == group_name:
                return group
        return {}

    def _groups(self, group_name):
        params = {"search": group_name}
        response = requests.get(f"{self.url}/groups", params=params, headers=self._headers)
        return json.loads(response.text)

    def _create_group(self, group_name):
        data = {"name": group_name, "path": group_name, "visibility": "private"}
        response = requests.post(f"{self.url}/groups", headers=self._headers, data=data, timeout=5)
        return json.loads(response.text)

    """项目操作"""
    @classmethod
    def get_project(cls, project_id):
        return requests.get(f"{cls.url}/projects/{project_id}", params=cls.params, headers=cls._headers)

    def get_project_from_name(self, project_name, group_name: str = ''):
        """ 获取项目
            1. 根据项目名调用模糊匹配API。（没有完全匹配）
            2. 过滤出项目名相等的项目，并返回。
            3. 无匹配则返回{}
        """
        if group_name == '':
            projects = self._search(project_name)
        else:
            projects = self._projects(group_name, project_name)
        projects = [p for p in projects if p['name'] == project_name]
        return (projects and projects[0]) or {}

    def _projects(self, group, project):
        response = requests.get(f"{self.url}/groups/", params={"search": group}, headers=self._headers)
        return requests.get(f"{self.url}/groups/{response.json()[0]['id']}/projects",
                            params={"search": project}, headers=self._headers).json()

    @classmethod
    def projects(cls, params):
        return requests.get(f"{cls.url}/projects/", params=params, headers=cls._headers).json()

    @classmethod
    def get_projects_with_namespace(cls, search, search_namespaces=True):
        """ 获取项目：根据命名空间path_with_namespace匹配
        """
        params = {
            "search": search,
            "search_namespaces": search_namespaces,
            'per_page': 100
        }
        return list(filter(lambda p: search == p['path_with_namespace'], cls.projects(params)))

    @classmethod
    def get_project_id(cls, path_with_namespace):
        """获取项目id"""
        return cls.get_projects_with_namespace(path_with_namespace)[0]['id']

    def create_project(self, group_name: str, project_name):
        """ 创建项目
            1. 创建项目组。（无需验证，已存在则API会告知）
            2. 创建项目。（无需验证，已存在则API会告知）
            3. 返回项π目信息。
        """
        group_name = group_name.lower()
        self._create_group(group_name)
        data = {"name": project_name, "namespace_id": self._get_group(group_name)['id']}
        requests.post(f"{self.url}/projects", headers=self._headers, data=data, timeout=5)
        return self.get_project_from_name(project_name, group_name)

    @classmethod
    def edit_project(cls, project_id, data):
        """更新项目"""
        return requests.put(f"{cls.url}/projects/{project_id}", headers=cls._headers, data=data)

    def _delete_project(self, group_name, project_name):
        """ 删除项目：Warning！！！切勿胡乱调用！！！
            group_name为空则会查询所有项目组下的
        """
        project_id = self.get_project_from_name(project_name, group_name)['id']
        response = requests.delete(f"{self.url}/projects/{project_id}", headers=self._headers)
        return json.loads(response.text)

    @classmethod
    def invitations(cls, project_id: int, user_id: str):
        """邀人入项目，
        :Params user_id: 新成员的 ID 或用逗号分隔的多个 ID。
        无访问权限 (0)
        最小访问权限 (5)
        访客 (10)
        计划员 (15)
        报告员 (20)
        开发者 (30)
        维护者 (40)
        所有者 (50)
        """
        data = {
          "access_level": 30,
          "user_id": user_id,   # 639,686
        }
        return requests.post(f"{cls.url}/projects/{project_id}/invitations", headers=cls._headers, data=data)

    """分支操作"""
    @classmethod
    def get_branch(cls, project_id, branch):
        """获取分支详情"""
        return requests.get(f"{cls.url}/projects/{project_id}/repository/branches/{urllib.parse.quote_plus(branch)}",
                           headers=cls._headers, timeout=10)

    @classmethod
    def branches(cls, project_id, params):
        return requests.get(f"{cls.url}/projects/{project_id}/repository/branches/",
                           params=params, headers=cls._headers).json()

    @classmethod
    def create_branch(cls, project_id, ref, branch):
        """创建代码库分支"""
        data = {"ref": ref, "branch": branch}
        return requests.post(f"{cls.url}/projects/{project_id}/repository/branches",
                           headers=cls._headers, data=data, timeout=10)

    @classmethod
    def delete_branch(cls, project_id, branch):
        """删除代码库分支"""
        return request.delete(f"{cls.url}/projects/{project_id}/repository/branches/{urllib.parse.quote_plus(branch)}",
                               headers=cls._headers, timeout=10)

    @classmethod
    def get_protected_branch(cls, project_id, branch):
        """获取保护仓库分支"""
        return requests.get(f"{cls.url}/projects/{project_id}/protected_branches/{urllib.parse.quote_plus(branch)}",
                            headers=cls._headers, timeout=10)

    @classmethod
    def protect_branch(cls, project_id, branch, **kwargs):
        """保护仓库分支"""
        data = {"name": branch, **kwargs}
        return requests.post(f"{cls.url}/projects/{project_id}/protected_branches",
                               headers=cls._headers, data=data, timeout=10)

    @classmethod
    def unprotect_branch(cls, project_id, branch):
        """取消保护仓库分支"""
        return requests.delete(f"{cls.url}/projects/{project_id}/protected_branches/{urllib.parse.quote_plus(branch)}",
                               headers=cls._headers, timeout=10)

    @classmethod
    def all_branches(cls, project_id, params: dict, iterations=20):
        """获取指定仓的所有分支
        :params project_id: 仓库ID
        :params params: 请求参数，一般{"per_page": 100}
        :params iterations: 获取总"""
        branches = []
        params.update({"per_page": 100})
        url = f"{cls.url}/projects/{project_id}/repository/branches/"
        for _ in range(iterations):
            response = requests.get(url, params=params, headers=cls._headers)
            branches.extend(response.json())
            url = response.links.get('next', {}).get('url')
            if not url:
                break
        return branches

    """流水线操作"""
    @classmethod
    def get_pipeline(cls, project_id, pipeline_id='', **kwargs) -> dict:
        return request.get(f"{cls.url}/projects/{project_id}/pipelines/{pipeline_id}",
                           headers=cls._headers, params={**cls.params, **kwargs}, timeout=10).json()

    @classmethod
    def get_pipelines(cls, project_id, **kwargs) -> dict:
        return request.get(f"{cls.url}/projects/{project_id}/pipelines/",
                           headers=cls._headers, params={**cls.params, **kwargs}, timeout=10).json()

    def run_pipeline(self, project_id: int, ref: str = 'refs/heads/develop_x3_orin', variables: dict = None):
        """触发流水线
        :params project_id 被触发的仓库ID
        :params ref 被触发的仓库所选用的分支
        :params variables 传递给被触发的Pipeline的参数"""
        data = {"ref": ref, "variables": variables or []}
        headers = self._headers.copy()
        headers.update({'Content-Type': 'application/json'})
        return request.post(f"{self.url}/projects/{project_id}/pipeline",
                            headers=headers, data=json.dumps(data), timeout=15)

    def retry(self, project_id: int, pipeline_id: int, **kwargs):
        """重试流水线
        :params project_id 被触发的仓库ID
        :params ref 被触发的仓库所选用的分支
        :params variables 传递给被触发的Pipeline的参数"""
        headers = self._headers.copy()
        headers.update({'Content-Type': 'application/json'})
        return request.post(f"{self.url}/projects/{project_id}/pipelines/{pipeline_id}/retry",
                            headers=headers, timeout=15)

    @classmethod
    def pipeline_cancel(cls, project_id: int, pipeline_id: int):
        return request.post(f"{cls.url}/projects/{project_id}/pipelines/{pipeline_id}/cancel",
                             headers=cls._headers, timeout=10)

    @classmethod
    def delete_pipeline(cls, project_id: int, pipeline_id: int):
        return requests.delete(f"{cls.url}/projects/{project_id}/pipelines/{pipeline_id}",
                             headers=cls._headers, timeout=10)

    @classmethod
    def get_jobs(cls, project_id: int, pipeline_id: int):
        return request.get(f"{cls.url}/projects/{project_id}/pipelines/{pipeline_id}/jobs",
                           headers=cls._headers, params=cls.params, timeout=10)

    @classmethod
    def all_jobs(cls, project_id: int, pipeline_id: int, params: dict = None, iterations=20):
        """获取指定仓的指定流水线的所有作业
        :params project_id: 仓库ID
        :params params: 请求参数，一般{"per_page": 100}
        :params iterations: 获取总"""
        jobs = []
        params = params or {}
        params.update({"per_page": 100})
        url = f"{cls.url}/projects/{project_id}/pipelines/{pipeline_id}/jobs/"
        for _ in range(iterations):
            response = request.get(url, params=params, headers=cls._headers)
            jobs.extend(response.json())
            url = response.links.get('next', {}).get('url')
            if not url:
                break
        return jobs

    def trace(self, project_id: int, job_id: int):
        response = request.get(f"{self.url}/projects/{project_id}/jobs/{job_id}/trace",
                               headers=self._headers, timeout=10)
        return response.content.decode('utf-8')

    """提交操作"""
    @classmethod
    def get_commit(cls, project_id, sha):
        """获取项目提交"""
        return requests.get(f"{cls.url}/projects/{project_id}/repository/commits/{sha}",
                           headers=cls._headers)

    """标签操作"""
    @classmethod
    def tag(cls, project_id, tag_name):
        """获取项目标签列表"""
        return request.get(f"{cls.url}/projects/{project_id}/repository/tags/{tag_name}",
                           headers=cls._headers).json()

    @classmethod
    def tags(cls, project_id, params):
        """获取项目标签列表"""
        return request.get(f"{cls.url}/projects/{project_id}/repository/tags/",
                           params=params, headers=cls._headers).json()

    @classmethod
    def get_tag(cls, project_id, tag_name):
        """获取项目标签"""
        return requests.get(f"{cls.url}/projects/{project_id}/repository/tags/{urllib.parse.quote_plus(tag_name)}",
                           headers=cls._headers, timeout=10)

    @classmethod
    def create_tag(cls, project_id, tag_name, ref):
        """创建新标签"""
        data = {
            "tag_name": tag_name,
            "ref": ref,
            "message": "标签由OPS平台自动创建"
        }
        return requests.post(f"{cls.url}/projects/{project_id}/repository/tags", headers=cls._headers, data=data)

    @classmethod
    def delete_tag(cls, project_id, tag_name):
        """删除标签"""
        return requests.delete(f"{cls.url}/projects/{project_id}/repository/tags/{urllib.parse.quote_plus(tag_name)}", headers=cls._headers)

    @classmethod
    def protected_tags(cls, project_id):
        """查看已经保护起来的标签"""
        return requests.get(f"{cls.url}/projects/{project_id}/protected_tags", headers=cls._headers)

    @classmethod
    def protect_tag(cls, project_id, tag_name):
        """保护标签
        0(或None): 无访问，即没有推送和合并权限。
        30(或Developer): 开发者访问，允许推送和合并。
        40(或Maintainer): 维护者访问，允许推送和合并，并管理分支保护设置
        60(或Admin): 管理员访问，拥有最高的推送、合并和设置权限。"""
        data = {
            "name": tag_name,
            "create_access_level": "0"
        }
        return requests.post(f"{cls.url}/projects/{project_id}/protected_tags", headers=cls._headers, data=data)

    @classmethod
    def unprotect_tag(cls, project_id, tag_name):
        """取消保护仓库标签"""
        return requests.delete(f"{cls.url}/projects/{project_id}/protected_tags/{urllib.parse.quote_plus(tag_name)}", headers=cls._headers)

    """合并请求操作"""
    @classmethod
    def search_merge_request(cls, project_id, source_branch, target_branch):
        """搜索出合并请求"""
        params = {
            "state": "opened",
            "source_branch": source_branch,
            "target_branch": target_branch,
        }
        return requests.get(f"{cls.url}/projects/{project_id}/merge_requests", headers=cls._headers, params=params)

    @classmethod
    def get_merge_request(cls, project_id, merge_request_iid):
        """获取合并请求详情"""
        return requests.get(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}", headers=cls._headers)

    @classmethod
    def create_merge_request(cls, project_id, source_branch, target_branch, title: str = None):
        """创建合并请求"""
        title = title or '由OPS自动创建的合并请求'
        data = {
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "skip_ci": True
        }
        return requests.post(f"{cls.url}/projects/{project_id}/merge_requests", headers=cls._headers, data=data)

    @classmethod
    def delete_merge_request(cls, project_id, merge_request_iid):
        """删除合并请求"""
        return requests.delete(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}", headers=cls._headers)

    @classmethod
    def get_merge_request_pipelines(cls, project_id, merge_request_iid):
        """列出合并请求流水线"""
        return requests.get(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}/pipelines", headers=cls._headers)

    @classmethod
    def diffs_merge_request(cls, project_id, merge_request_iid):
        """列出合并请求差异"""
        return requests.get(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}/diffs", headers=cls._headers)

    @classmethod
    def merge_merge_request(cls,
                            project_id,
                            merge_request_iid,
                            should_remove_source_branch=False,
                            merge_commit_message=None):
        """合并合并请求"""
        data = {
            "should_remove_source_branch": should_remove_source_branch,   # 如果为 true，则删除源分支。
            "merge_commit_message": merge_commit_message,
        }
        return requests.put(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}/merge", headers=cls._headers, data=data)

    @classmethod
    def update_merge_request(cls, project_id, merge_request_iid, data):
        """更新合并请求"""
        return requests.put(f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}", headers=cls._headers, data=data)

    @classmethod
    def close_merge_request(cls, project_id, merge_request_iid):
        """关闭合并请求"""
        data = {
            "state_event": "close",  # close, reopen
        }
        return cls.update_merge_request(project_id=project_id, merge_request_iid=merge_request_iid, data=data)

    """Runner相关"""
    @classmethod
    def get_runners(cls, group_id=None, project_id=None, **kwargs):
        """获取Runner列表"""
        params = {}
        path_inner = group_id and '/groups/{}'.format(group_id) or ''
        path_inner = path_inner or (project_id and '/projects/{}'.format(project_id) or '')
        return request.get(f"{cls.url}{path_inner}/runners",
                           headers=cls._headers,
                           params={**cls.params, **params, **kwargs})

    @classmethod
    def get_runner(cls, runner_id):
        """获取Runner信息"""
        return request.get(f"{cls.url}/runners/{runner_id}", headers=cls._headers)

    @classmethod
    def get_runner_jobs(cls, runner_id, **kwargs):
        """获取Runner信息"""
        return requests.get(f"{cls.url}/runners/{runner_id}/jobs", params={**cls.params, **kwargs}, headers=cls._headers)

    @classmethod
    def get_project_files(cls, project_id, ref, path):
        """获取仓库文件列表"""
        encoded_path = urllib.parse.quote(path, safe='')
        return requests.get(f"{cls.url}/projects/{project_id}/repository/files/{encoded_path}?ref={ref}",
                            headers=cls._headers)

    @classmethod
    def add_group_member(cls, group_id, user_id, access_level=30):
        """添加用户到群组
        :param group_id: 群组ID
        :param user_id: 用户ID（必须是GitLab中的有效用户ID）
        :param access_level: 访问级别
            无访问权限 (0)
            最小访问权限 (5)
            访客 (10)
            计划员 (15)
            报告员 (20)
            开发者 (30)
            维护者 (40)
            所有者 (50)
        """
        data = {
            "user_id": user_id,
            "access_level": access_level
        }
        return requests.post(f"{cls.url}/groups/{group_id}/members", headers=cls._headers, data=data)

    @classmethod
    def remove_group_member(cls, group_id, user_id):
        """从群组中移除用户"""
        return requests.delete(f"{cls.url}/groups/{group_id}/members/{user_id}", headers=cls._headers)

    @classmethod
    def delete_group_member(cls, group_id, user_id):
        return cls.remove_group_member(group_id, user_id)

    @classmethod
    def get_user_by_username(cls, username):
        """根据用户名获取GitLab用户信息"""
        params = {"username": username}
        response = requests.get(f"{cls.url}/users", params=params, headers=cls._headers)
        users = response.json()
        # 返回匹配的第一个用户
        for user in users:
            if user.get('username') == username:
                return user
        return None

    @classmethod
    def add_project_member(cls, project_id, user_id, access_level=GitlabAccessLevel.DEVELOPER):
        """添加用户到项目"""
        data = {
            "user_id": user_id,
            "access_level": int(access_level)
        }
        return requests.post(f"{cls.url}/projects/{project_id}/members", headers=cls._headers, data=data)

    @classmethod
    def remove_project_member(cls, project_id, user_id):
        """从项目移除用户"""
        return requests.delete(f"{cls.url}/projects/{project_id}/members/{user_id}", headers=cls._headers)

    @classmethod
    def delete_project_member(cls, project_id, user_id):
        return cls.remove_project_member(project_id, user_id)

    @classmethod
    def get_accessible_projects(cls, group_id):
        """获取群组中可访问的项目"""
        all_projects = []
        page = 1
        while True:
            params = {
                "per_page": 50,
                "page": page,
                "include_subgroups": "true"
            }
            response = requests.get(f"{cls.url}/groups/{group_id}/projects", params=params, headers=cls._headers)
            if response.status_code != 200:
                log.error('Failed to fetch projects: status_code=%s, response=%s', response.status_code, response.text)
                break

            projects = response.json()
            if not projects:
                break

            all_projects.extend(projects)
            page += 1

            # 检查是否有下一页
            link_header = response.headers.get('Link', '')
            if 'rel="next"' not in link_header:
                break
        log.info('Fetched %d projects', len(all_projects))
        return all_projects

    @classmethod
    def get_all(cls, url, params):
        output = []
        while url:
            resp = requests.get(url, params=params, headers=cls._headers)
            if resp.status_code != 200:
                log.error(f'get_all {url}, params={params}, status_code={resp.status_code}, text={resp.text}')
                break

            output.extend(resp.json())
            url = resp.links.get('next', {}).get('url')

        return output

    @classmethod
    def get_mrs_by_project_id(cls, project_id, state="opened", wip="no", updated_after=None):
        params = {"per_page": 100, "state": state, "wip": wip}
        if updated_after is not None:
            params["updated_after"] = updated_after

        url = f"{cls.url}/projects/{project_id}/merge_requests"
        mr_list = cls.get_all(url=url, params=params)
        return mr_list

    @classmethod
    def get_mrs_by_branches(cls, source_branch, target_branch, state="opened", wip="no", updated_after=None):
        url = f"{cls.url}/merge_requests"
        params = {
            "per_page": 100,
            "scope": "all",
            "state": state,
            "wip": wip,
        }
        if updated_after is not None:
            params["updated_after"] = updated_after

        if source_branch:
            params["source_branch"] = source_branch

        if target_branch:
            params["target_branch"] = target_branch

        return cls.get_all(url=url, params=params)

    @classmethod
    def get_all_projects(cls):
        url = f"{cls.url}/projects"
        params = {"per_page": 100}
        return cls.get_all(url=url, params=params)

    @classmethod
    def search_projects(cls, name):
        url = f"{cls.url}/projects"
        params = {
            "per_page": 100,
            "search": name,
        }
        return requests.get(url, headers=cls._headers, params=params).json()

    @classmethod
    def search_project_branches(cls, project_id, search):
        url = f"{cls.url}/projects/{project_id}/repository/branches"
        params = {
            "per_page": 100,
            "search": search,
        }
        return requests.get(url, headers=cls._headers, params=params).json()

    @classmethod
    def add_merge_note(cls, project_id, merge_request_iid, body):
        url = f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}/notes"
        return requests.post(url, json={"body": body}, headers=cls._headers).json()

    @classmethod
    def get_single_mr(cls, project_id, merge_request_iid):
        url = f"{cls.url}/projects/{project_id}/merge_requests/{merge_request_iid}/"
        return requests.get(url, headers=cls._headers).json()

    @classmethod
    def search_users(cls, search):
        url = f"{cls.url}/users"
        return requests.get(url, headers=cls._headers, params={"search": search}).json()

    @classmethod
    async def aget_group_projects(cls, group_id):
        output = []
        url = f"{cls.url}/groups/{group_id}/projects"
        params = {
            "per_page": 100,
            "include_subgroups": "true"
        }

        async with aiohttp.ClientSession() as session:
            while url:
                async with session.get(url, headers=cls._headers, params=params) as response:
                    if response.status != 200:
                        log.error("aget_group_projects failed with status=%s", response.status)
                        break

                    body = await response.json()
                    if not body:
                        break

                    output.extend(body)
                    url = response.links.get('next', {}).get('url')

        return output

    @classmethod
    async def aget_project_branch(cls, project_id, branch):
        url = f"{cls.url}/projects/{project_id}/repository/branches/{urllib.parse.quote_plus(branch)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=cls._headers) as response:
                if response.status != 200:
                    return None

                return await response.json()

    @classmethod
    async def acreate_merge_request(cls,project_id, source_branch, target_branch, title, skip_ci=False, assignee_ids=None):
        data = {
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "skip_ci": skip_ci
        }

        if assignee_ids is not None:
            data["assignee_ids"] = assignee_ids  # The ID of the users to assign the merge request to.

        url = f"{cls.url}/projects/{urllib.parse.quote_plus(project_id)}/merge_requests"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=cls._headers) as response:
                return await response.json()

    @classmethod
    def run_job(cls, project_id, job_ids):
        url = f"{cls.url}/projects/{project_id}/jobs/{job_ids}/play"
        return requests.post(url, headers=cls._headers)

    @classmethod
    def get_job(cls, project_id, job_ids):
        url = f"{cls.url}/projects/{project_id}/jobs/{job_ids}"
        return requests.get(url, headers=cls._headers).json()

    @classmethod
    def repository_compare(cls, project_id, from_, to):
        url = f"{cls.url}/projects/{urllib.parse.quote_plus(str(project_id))}/repository/compare"
        return request.get(url, headers=cls._headers, params={"from": from_, "to": to}).json()

    @classmethod
    def get_branches_diff(cls, project_id, source_branch, target_branch):
        return cls.repository_compare(project_id, from_=target_branch, to=source_branch)

    @classmethod
    def get_all_groups(cls):
        url = f"{cls.url}/groups"
        params = {"per_page": 100}
        return cls.get_all(url=url, params=params)

    @classmethod
    def update_group_member_access_level(cls, group_id, user_id, access_level):
        url = f"{cls.url}/groups/{group_id}/members/{user_id}"
        return requests.put(url, headers=cls._headers, json={"access_level": access_level})

    @classmethod
    def update_project_member_access_level(cls, project_id, user_id, access_level):
        url = f"{cls.url}/projects/{project_id}/members/{user_id}"
        return requests.put(url, headers=cls._headers, json={"access_level": access_level})

    @classmethod
    def group_member(cls, group_id, gitlab_userid):
        url = f"{cls.url}/groups/{group_id}/members/{gitlab_userid}"
        return requests.get(url, headers=cls._headers)

    @classmethod
    def project_member(cls, project_id, gitlab_userid):
        url = f"{cls.url}/projects/{project_id}/members/{gitlab_userid}"
        return requests.get(url, headers=cls._headers)
