# -*- coding:utf-8 -*-
import os
import re
import sys
import copy
import math
import json
import heapq
import socket
import shutil
import hashlib
import inspect
import argparse
import platform
import traceback
import subprocess

from xml.dom import minidom
from xml.etree import ElementTree
from datetime import datetime, timedelta, timezone


class Methods:
    @staticmethod
    def get_stacks():
        """获取调用栈信息"""
        stacks = traceback.format_stack()
        return ''.join(stacks[: -1 if len(stacks) > 1 else None]).rstrip('\n')

    @staticmethod
    def get_stack_funcs(max_depth=12, head=0, tail=1):
        """获取调用栈的方法链路
        :param max_depth: 最大深度
        :param head: 头部过滤，默认head=0时，将显示全调用链路的全栈，设为1时将过滤头部一条
        :param tail: 尾部过滤，默认tail=1时，将不显示调用链路的尾路get_stack_funcs方法"""
        try:
            if True:
                frame, stack = sys._getframe(), []
                while frame:
                    stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
                    frame = frame.f_back
            else:
                stack = [frame[1:] for frame in inspect.stack()[:]]

            head = len(stack) - head
            # frame: 0: 帧对象(内存地址) 1：方法文件
            #       2：调用发生行 3：方法名
            #       4：帧上下文（代码行内容字符串）
            #       5：当前调用栈的索引；inspect.stack()只取当前行的索引，因此始终为0
            func_names = ["{}.{}".format(frame[2], frame[1]) for frame in stack[tail:head][::-1]]
            # 限制最大深度显示
            if max_depth:
                func_names = func_names[-max_depth:]
                if len(stack) > max_depth:
                    func_names.insert(0, '...')
        except Exception as e:
            traceback.print_exception(type(e), e, sys.exc_info()[2])
            func_names = ['None']
        return ".".join(func_names)

    @staticmethod
    def get_frame(index=1):
        """获取调用栈"""
        return sys._getframe(index)

    @classmethod
    def get_cur_func_name(cls):
        """获取当前调用的方法名"""
        # return cls.get_frame(2).f_back.f_code.co_name
        return cls.get_frame(2).f_code.co_name

    @staticmethod
    def run_cmd(cmd, silence=True, log=print) -> str:
        """执行系统命令，一般为shell"""
        if not silence:
            log(cmd)
        return ''.join(subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, text=True).stdout.readlines()).strip()

    @staticmethod
    def run_cmd_with_timeout(cmd, timeout=None):
        """执行命令（附带超时）"""
        try:
            return '\n'.join(subprocess.run(cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout,
                check=True, text=True
            ).stdout.splitlines())
        except subprocess.TimeoutExpired:
            return 'Command timed out!'
        except subprocess.CalledProcessError as e:
            return f"Command failed with code {e.returncode}: {e.stderr}"

    @staticmethod
    def run_cmd_with_code(cmd, timeout=None):
        """执行命令（返回退出码）"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out!"

    @staticmethod
    def check_call(cmds):
        """执行系统命令，一般为shell"""
        return subprocess.check_call(cmds)

    @classmethod
    def run_cmds(cls, cmds):
        """执行系统命令，一般为shell"""
        return cls.check_call(cmds)

    @staticmethod
    def run_func_safely(func, *args, **kwargs):
        """运行地运行方法"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exception(type(e), e, sys.exc_info()[2])

    @classmethod
    def checking_file_exists(cls, path, file_name):
        """检查文件是否存在"""
        return cls.run_cmd("find {} -mindepth 1 -maxdepth 2 -type f -name *{}*".format(path, file_name))

    @staticmethod
    def makedirs(folder):
        """创建文件夹，类似于：mkdir -p folder"""
        if not os.path.exists(folder):   # 如果文件夹不存在，则创建，如：os.makedirs(folder, exist_ok=True)
            os.makedirs(folder)     # py2中无法使用exist_ok=True参数，那是py3.2之后添加的特性

    @staticmethod
    def remove_file_or_folder(path):
        """移除文件或目录"""
        try:
            os.remove(path)
        except OSError:
            try:
                shutil.rmtree(path)
            except OSError:
                pass

    @staticmethod
    def get_distance(center_point, dst_point):
        """求两点之间的距离
        :param center_point: 中心点，示例数据 - {'x': 0, 'y': 0, 'z': 0}    # xyz均为可选值
        :param dst_point: 目标点，示例数据 -  {'x': 1, 'y': 1, 'z': 0}  # xyz均为可选值
        :return: 两点之间的距离，示例数据 - 1.53"""
        distance_dict = {k: dst_point[k] - center_point[k] for k in ['x', 'y', 'z']
                         if k in dst_point and k in center_point}
        # return sum([v ** 2 for k, v in distance_dict.items()]) ** 0.5
        return math.hypot(*distance_dict.values())  # 用向量求模，耗时仅有平方和开根的60%

    @staticmethod
    def is_over_threshold(value_list, threshold, rate=0.8, greater=True):
        """判断value_list中的超过阈值的数据是否超过指定百分比"""
        if len(value_list) < 10:    # 数据长度小于10，不做处理
            return False
        if greater:
            over_threshold_list = list(filter(lambda temp: temp > threshold, value_list))
        else:
            over_threshold_list = list(filter(lambda temp: temp <= threshold, value_list))
        return len(over_threshold_list) > len(value_list) * rate

    @staticmethod
    def deduplicate(data_list):
        """列表去重"""
        return list(set(data_list))

    @staticmethod
    def _get_inter_or_diff(func_name, *args, **kwargs):
        """获取集合群的交集或差集
        :param func_name: 传入的求集合交集或差集名；参数如下：intersection_update、difference_update
        :param args: [set(), set()]；传入多个集合
        :param kwargs: {set1: set(), set2: set()}"""
        args += tuple(kwargs.values())
        if len(args) == 0:
            return set()
        if len(args) == 1:
            return set(args[0])
        result = set(args[0])
        return [getattr(result, func_name)(item) for item in args[1:]] and result

    @classmethod
    def get_intersection(cls, *args, **kwargs):
        """获取集合群的交集"""
        return cls._get_inter_or_diff('intersection_update', *args, **kwargs)

    @classmethod
    def get_difference(cls, *args, **kwargs):
        """获取集合群的差集"""
        return cls._get_inter_or_diff('difference_update', *args, **kwargs)

    @classmethod
    def is_intersected(cls, *args, **kwargs):
        """判断两个集合是否有交集"""
        return bool(cls.get_intersection(*args, **kwargs))

    @staticmethod
    def dict_to_md5(d):
        """获取字典的md5值"""
        d_json = json.dumps(d, sort_keys=True)  # sort_keys=True 保证键的顺序相同
        return hashlib.md5(d_json.encode('utf-8')).hexdigest()  # 返回md5值

    @staticmethod
    def get_offset(center_point, dst_point):
        """求两点之间的偏移量
        :param center_point: 中心点，示例数据 - {'x': 0, 'y': 0} 或 (0, 0)
        :param dst_point: 目标点，示例数据 -  {'x': 1, 'y': 1} 或 (1, 1)
        :return: (x偏移量, y偏移量)"""
        if type(center_point) is tuple and type(dst_point) is tuple:
            distance_x = dst_point[0] - center_point[0]
            distance_y = dst_point[1] - center_point[1]
        else:   # params type are dict
            distance_x = dst_point['x'] - center_point['x']
            distance_y = dst_point['y'] - center_point['y']
        return distance_x, distance_y

    @staticmethod
    def convert_to_unicode(s):
        """转化成unicode编码（ascii码不在影响范围内）"""
        return json.dumps(s, ensure_ascii=True)[1:-1]  # [1:-1] 是为了去掉开始和结束的双引号

    @staticmethod
    def convert_to_2dim(src_list, sub_list_len=3, drop_exceed=True):
        """转一维列表转为2维列表
        :param src_list: 源一维列表
        :param sub_list_len: 第二维列表长度
        :param drop_exceed: 当数据不满足第二维长度时，是否丢弃
        :return 二维列表"""
        return [src_list[col:col + sub_list_len]
                for col in range(0, len(src_list), sub_list_len)
                if not drop_exceed or len(src_list[col:col + sub_list_len]) == sub_list_len]

    @staticmethod
    def filter_extreme_values(src_list, smallest_len=1, largest_len=1):
        """过滤波峰波谷数据点（风险，获取过程非原子，过程中列表发生了变化就会抛异常，所以需要给对象加锁）
        :param src_list 数字列表
        :param smallest_len: 过滤掉最小的N个数
        :param largest_len: 过滤掉最大的N个数
        :return 过滤后的src_list列表（长度要大于最大最小长度和，否则不过滤）
        """
        try:
            src_list_copy = copy.deepcopy(src_list)
            smallest = heapq.nsmallest(smallest_len, src_list_copy)
            largest = heapq.nlargest(largest_len, src_list_copy)
            return [col for col in src_list_copy if col not in smallest and col not in largest] or src_list_copy
        except Exception as e:
            traceback.print_exception(type(e), e, __import__('sys').exc_info()[2])
            return src_list

    @staticmethod
    def get_iterm_suffix_with(data, suffix='_emergency_stop'):
        """获取以suffix结尾的key的键值对（仅第一、第二层字典）
        获取第二层的代码解释，执行顺序如下：
            for v in data.values(): 这是最外层的循环，它遍历data字典中的所有值。
            if isinstance(v, dict): 对于每个值v，检查它是否是一个字典。
            for sub_k, sub_v in v.items(): 如果v是一个字典，那么这个内部循环会遍历这个字典的键值对。
            if sub_k.endswith(suffix): 对于每个键值对，检查键sub_k是否以suffix字符串结尾。
            sub_v: 如果键以指定的后缀结尾，那么这个值sub_v就会被收集到最终的列表中。
        :param data: 字典数据
        :param suffix: 后缀
        :return: 符合条件的键值对字典；{"abc_emergency_stop": 1, "cba_emergency_stop": 0}
        """
        # 查找第一层中满足条件的键值对
        found_keys = {k: v for k, v in data.items() if k.endswith(suffix)}

        # 查找第二层中满足条件的键值对
        found_keys.update({
            sub_k: sub_v
            for v in data.values() if isinstance(v, dict)
            for sub_k, sub_v in v.items() if sub_k.endswith(suffix)
        })

        return found_keys

    @staticmethod
    def removeprefix(s, prefix):
        """移除字符串前缀
        # lstrip为移除左侧字符集而不是字符串，removeprefix在py3.9中才有"""
        return s[len(prefix):] if s.startswith(prefix) else s

    @staticmethod
    def removesuffix(s, suffix) -> str:
        """移除字符串前缀
        # rstrip为移除左侧字符集而不是字符串，removesuffix在py3.9中才有"""
        return s[:-len(suffix)] if s.endswith(suffix) else s

    @staticmethod
    def get_int(value):
        """安全的转为整形"""
        try:
            return int(value)
        except (ValueError, TypeError, OverflowError):
            return 0

    @staticmethod
    def get_float(value):
        """安全的转为浮点形"""
        try:
            return float(value)
        except (ValueError, TypeError, OverflowError):
            return 0.

    @staticmethod
    def loads(value):
        """安全的转为字典"""
        try:
            if type(value) is dict:
                return value
            return json.loads(value)
        except (ValueError, TypeError, OverflowError) as e:
            traceback.print_exception(type(e), e, sys.exc_info()[2])
            return {}

    @staticmethod
    def get_system_info():
        """判断当前系统
        1. Parallels
        2. native Ubuntu machine
        3. Docker container
        4. Darwin
        5. and so on"""
        system = platform.system()
        if system == 'Linux':
            if os.path.exists('/.dockerenv'):
                return "Running inside a Docker container on Ubuntu"
            else:
                try:
                    virtualization = subprocess.check_output(['systemd-detect-virt']).strip()
                    if virtualization == b'parallels':
                        return "Running inside Parallels virtual machine"
                    elif virtualization == b'none':
                        return "Running on a native Ubuntu machine"
                    else:
                        return "Running inside a virtualized environment: {}".format(virtualization.decode())
                except subprocess.CalledProcessError:
                    return "Could not determine virtualization status"
        else:
            return "Running on {}".format(system)

    @staticmethod
    def extract_ips_from_string(text):
        """提取字符串中的所有的IPv4地址
        :param text
        :return []"""
        # 正则表达式模式，用于简易的匹配IP地址（非严格IP格式）
        return re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)

    @staticmethod
    def resort_content_no(string, pattern=r'\d+'):
        """重排序所匹配到的内容"""
        current_number = [1]
        prefix = re.sub(r'\\d\+.*', '', pattern)
        subfix = re.sub(r'.*\\d\+', '', pattern)

        def replace_match(match):
            replacement = f"{prefix}{current_number[0]}{subfix}"
            current_number[0] += 1
            return replacement
        return re.sub(pattern, replace_match, string)

    @staticmethod
    def get_file_list(file_path, postfix):
        """读取指定文件夹内的所有文件成一个字符串列表
        如：[conf/path_maps/perception.xml, conf/path_maps/pnc.xml]
        :param file_path conf/path_maps
        :param postfix xml"""
        return [os.path.join(root, f) for root, dirs, files in os.walk(file_path)
                for f in files if f.endswith(f".{postfix.lstrip('.')}")]

    @staticmethod
    def read_json(file_path):
        """将json数据读取为json(dict)数据
        :param file_path conf/conf.json"""
        with open(file_path, 'r') as file:
            return json.loads(file.read())

    @staticmethod
    def write_to_json(data_json, file_path):
        """将json数据写入json文件中
        :param data_json json数据 {}
        :param file_path 文件路径 conf/conf.json"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data_json, indent=4))

    @staticmethod
    def read_yml(file_path):
        """将yaml数据读取为json(dict)数据
        :param file_path conf/conf.yml
        需要pyyaml库"""
        with open(file_path, 'r') as file:
            return __import__('yaml').safe_load(file)

    @staticmethod
    def write_to_yaml(data_json, file_path):
        """将json数据写入yaml文件中
        :param data_json json数据 {}
        :param file_path conf/conf.yml
        需要pyyaml库"""
        with open(file_path, 'w', encoding='utf-8') as yaml_file:
            __import__('yaml').dump(data_json, yaml_file, allow_unicode=True, sort_keys=False)

    @classmethod
    def read_xml_to_dict(cls, xml: str) -> dict:
        """将xml读取成字典数据"""
        result = {}
        root = ElementTree.parse(xml).getroot() if xml.endswith('.xml') else ElementTree.fromstring(xml)
        for child in root:
            for node in child.iter():
                if node.tag == 'include' and 'name' in node.attrib:
                    result.update(cls.read_xml_to_dict(node.attrib.pop('name')))
                if node.tag not in result:
                    result[node.tag] = node.attrib
                elif type(result[node.tag]) is not list:
                    result[node.tag] = [result[node.tag], node.attrib]
                else:
                    result[node.tag].append(node.attrib)
        return result

    @classmethod
    def writ_dict_to_xml(cls, data: dict, filename: str = 'output.xml', title_name: str = 'manifest'):
        """将字典写入成xml文件"""
        # 1. 将dict转为xml
        manifest = ElementTree.Element(title_name)
        # 将字符串解析为元素并添加到 projects 元素
        for elem_name, elem in data.items():
            if type(elem) is list:
                for attrib in elem:
                    manifest.append(manifest.makeelement(elem_name, attrib))    # 添加子元素
            else:
                ElementTree.SubElement(manifest, elem_name, attrib=elem)  # 添加子元素
        # 2. 将XML格式化为字符串
        xml_str = ElementTree.tostring(manifest, encoding='utf-8', method='xml')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # 3. 将xml内容写入文件
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(pretty_xml_str)

        return pretty_xml_str

    @staticmethod
    def get_local_ip():
        """获取本机IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # 创建一个 UDP 套接字（不需要实际连接）
            s.connect(('8.8.8.8', 80))  # 连接到公共 DNS 服务器
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            traceback.print_exception(e)
            return '127.0.0.1'  # 失败时返回本地回环地址

    @staticmethod
    def to_datetime(dt):
        """将时间转换为日期时间"""
        if isinstance(dt, float):     # 时间戳浮点数转日期格式
            return datetime.fromtimestamp(dt * (0.001 if dt > 5572207999 else 1))   # 5572207999 -> 2146-07-30 11:33:19.000
        elif isinstance(dt, str):     # 日期字符串转日期格式
            if 'Z' in dt:
                return datetime.fromisoformat(dt.replace('Z', '+00:00'))
            else:
                dt = float(dt)
                return datetime.fromtimestamp(dt * (0.001 if dt > 5572207999 else 1))  # 5572207999 -> 2146-07-30 11:33:19.000
        return dt

    @classmethod
    def format_timedelta(cls, datetime_start, datetime_end=datetime.now()):
        """格式化时间差"""
        # 0. 数据兼容性处理
        datetime_start = cls.to_datetime(datetime_start)
        datetime_end = cls.to_datetime(datetime_end)
        # 转UTC转CST时间
        datetime_start = datetime_start.astimezone(timezone(timedelta(hours=8)))
        datetime_end = datetime_end.astimezone(timezone(timedelta(hours=8)))

        # 1. 获取日期差的自定义格式
        time_delta = datetime_end - datetime_start
        total_seconds = time_delta.total_seconds()
        days, remainder = divmod(total_seconds, 86400)  # 86400秒=1天
        hours, remainder = divmod(remainder, 3600)  # 3600秒=1小时
        minutes, seconds = divmod(remainder, 60)  # 60秒=1分钟
        if days > 0:
            return f"{days:.0f}d {hours:.0f}h {minutes:.0f}m {seconds:.1f}s"
        elif hours > 0:
            return f"{hours:.0f}h {minutes:.0f}m {seconds:.1f}s"
        elif minutes > 0:
            return f"{minutes:.0f}m {seconds:.1f}s"
        return f"{seconds:.2f}s"

    @staticmethod
    def read_args(kwargs: list = None) -> argparse.Namespace:
        """读取运行脚本传入参数
        kwargs在此处代表python main.py --kwarg=1的参数"""
        kwargs = kwargs or []
        parser = argparse.ArgumentParser(description='Process some integers.')
        for kwarg in kwargs:
            parser.add_argument(f"--{kwarg.lstrip('--')}", nargs=1)
            parser.add_argument(f"-{kwarg.lstrip('-')}", nargs=1)
        parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments for the command')
        args, _ = parser.parse_known_args()
        return args.args

    @classmethod
    def mask_sensitive_data(cls, data: dict) -> dict:
        """递归遍历字典，替换敏感字段"""
        sensitive_key = ['password', 'access_token', 'secret']
        data = copy.deepcopy(data)
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = cls.mask_sensitive_data(value)  # 递归处理嵌套字典
            elif key in sensitive_key and not isinstance(value, dict):
                data[key] = hashlib.sha256(value.encode()).hexdigest()    # 替换敏感字段
                data[key] = f"{data[key][:6]}{'*' * 52}{data[key][-6:]}"
        return data

    @classmethod
    def mask_sensitive_str(cls, text: str) -> str:
        """替换多种敏感信息为星号"""
        keywords = '|'.join([
            "secretKey", "Cookie", "apiKey",
            "password", "PRIVATE-TOKEN",
            "Authorization", "app_secret", "tenant_access_token",
            "user_id", "email", "mobile"])
        for d in ['"', "'"]:    # delimiter
            text = re.sub(
                rf'({d}(?:{keywords}){d}\s*:\s*{d})([^{d}]*)({d})',
                lambda m: f'{m.group(1)}{"*" * min(len(m.group(2)), 16)}{m.group(3)}',
                text
            )
        return text

    @classmethod
    def deep_merge(cls, src: dict, dst: dict, is_deep_copy: bool = True) -> dict:
        """递归合并字典（不覆盖src存在而dst不存在的值），返回新字典，不修改原字典"""
        src_copy = is_deep_copy and copy.deepcopy(src) or src
        for k, v in dst.items():
            if k in src_copy and isinstance(src_copy[k], dict) and isinstance(v, dict):
                src_copy[k] = cls.deep_merge(src_copy[k], v, is_deep_copy)  # 递归合并嵌套字典
            else:
                src_copy[k] = v  # 否则直接赋值
        return src_copy

    @staticmethod
    def list_json_2_json(data: list, key='key', value='value') -> dict:
        """json列表转json
        :Param data: 数据源
        :Param key: 从数据源中读取作为结果中key的字段
        :Param value: 从数据源中读取作为结果中value的字段
        :return result: dict"""
        result = {}
        for datum in data:
            result[datum[key]] = datum[value]
        return result

    @staticmethod
    def generate_unique_id(data: list) -> str:
        """为列表生成唯一字符串ID
        相同列表总是生成相同的ID、不同顺序ID不同
        """
        data = list(data)
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))  # 使用JSON确保序列化的一致性
        return hashlib.md5(json_str.encode('utf-8')).hexdigest()  # 生成MD5哈希作为字符串ID

    @classmethod
    def is_over_datetime(cls, datetime_target, **kwargs) -> bool:
        """判断时间是否超过: days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0"""
        return cls.to_datetime(datetime_target) > datetime.now(timezone.utc) - timedelta(**kwargs)

    @classmethod
    def is_under_datetime(cls, datetime_target, **kwargs) -> bool:
        """判断时间是否低于"""
        return cls.to_datetime(datetime_target) < datetime.now(timezone.utc) - timedelta(**kwargs)
