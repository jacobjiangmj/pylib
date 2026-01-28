# coding: utf-8
import os
import sys
import time
import json
import datetime
import traceback

from pylib.methods import Methods


class _Log:
    """格式化日志打印（不采用logging，也不采用loguru）
    注意！！！切不可在Cython编译后的文件中使用，也不可在编译成lib后的文件中使用，仅可在.py文件中使用"""
    _is_colorize = True     # 是否使用带有颜色的日志
    _throttle_time = {}  # 限流时间
    # 日志打印等级：DEBUG < INFO < WARNING < ERROR < CRITICAL
    # 不可直接使用_color_map_level.keys()，因为py2和py3的字典顺序不一样
    _levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS', 'EXCEPTION']
    _level = 0  # 向_levels的下标取值
    is_rospy = False    # 是否附加ros_node的打印
    mask_sensitive_str = True

    # 红色：31
    # 绿色：32
    # 黄色：33
    # 蓝色：34
    # 青色：36
    # 红色背景：41
    # 加粗：1
    # 重置：0
    _color_map_level = {
        'DEBUG': '\033[34m\033[1m',     # 蓝色
        'INFO': '\033[1m',              # 默认色：白色
        'WARNING': '\033[33m\033[1m',   # 黄色
        'ERROR': '\033[31m\033[1m',     # 红色
        'CRITICAL': '\033[41m\033[1m',  # 红色背景
        'SUCCESS': '\033[32m',  # 绿色
        'EXCEPTION': '\033[31m\033[1m',     # 红色
    }

    @classmethod
    def _colorize(cls, log_format, level='INFO'):
        """给日志加上颜色（使用shell颜色，类似于loguru）"""
        color_map = {
            '<green>': '\033[32m',
            '<cyan>': '\033[36m',
            '<level>': cls._color_map_level[level.upper()],
            '</green>': '\033[0m',
            '</cyan>': '\033[0m',
            '</level>': '\033[0m',
        }
        for key, value in color_map.items():
            log_format = log_format.replace(key, value)
        return log_format

    @staticmethod
    def _removeprefix(s, prefix):
        """移除字符串前缀
        # lstrip为移除左侧字符集而不是字符串，removeprefix在py3.9中才有"""
        return s[len(prefix):] if s.startswith(prefix) else s

    @staticmethod
    def _get_frame(index=1):
        """获取调用栈"""
        return sys._getframe(index)

    @classmethod
    def _get_caller_info(cls, **kwargs):
        """获取调用者信息
        本类调用栈：_get_caller_info -> _get_log_format -> _log -> debug/info/warning/error/critical/log
        :kwargs: 关键字参数： index: 调用者的索引，默认0表示调用log.log处，1表示调用log.log的上一层，以此类推"""
        # stack = [frame[1:] for frame in inspect.stack()[:]]
        # sys._getframe方法比inspect.stack()更为高效；后者常出现效率极低的情况；耗时几十，甚至上百毫秒
        frame, stack = cls._get_frame(), []
        while frame:
            stack.append((frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name))
            frame = frame.f_back

        # 条件1. 如果剩余调用栈只有1栈，说明本类调用者不可被链路追踪获取，就用最后一个调用栈为其展示
        # 条件2. 支持本类内部多次再调用，会将其过滤掉
        # 剔除部分调用栈
        while len(stack) > 1:
            if os.path.basename(stack[0][0]) not in ['log.py', 'decorator.py', 'timeit_decorator.py']:
                break
            stack = stack[1:]

        caller_frame = list(stack[min(kwargs.get('index', 0), len(stack) - 1)])  # 默认调用者为剩余调用栈的第0个元素
        caller_file = '/'.join(caller_frame[0].split('/')[-3:])
        caller_line = caller_frame[1]
        caller_function = caller_frame[2]

        # ros定制：按顺序移除lib/, dist-packages/, guardian/, decision_center/前缀
        for prefix in ['lib/', 'dist-packages/', 'guardian/', 'decision_center/']:
            caller_file = cls._removeprefix(caller_file, prefix)

        return caller_file, caller_function, caller_line

    @classmethod
    def _get_log_format(cls, level, *args, **kwargs):
        """获取日志格式"""
        # 参数准备
        caller_info = cls._get_caller_info(**kwargs)
        # 获取cst时间
        utc_time = datetime.datetime.utcnow()
        cst_time = utc_time + datetime.timedelta(hours=8)
        cst_time = cst_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        # 获取节流间隔
        period = kwargs.get('period', 0)  # 添加限流的日志提示
        period = period if type(period) in [int, float] else 0
        period = '[<cyan>period</cyan>.<cyan>{}</cyan>]'.format(round(period, 2)) if period > 0 else ''
        # ros定制：将ros node name显示在日志栏上
        ros_node = ''
        if cls.is_rospy:
            ros_node = __import__('rospy').get_name().lstrip('/')
            # ros_node = '[<cyan>{}</cyan>]'.format(ros_node)\
            #     if not caller_info[0].replace('.py', '').endswith(ros_node) else ''
            ros_node = '[<cyan>{}</cyan>]'.format(ros_node)

        # 获取format日志
        if cls._is_colorize:
            log_format = '[<green>{}</green>]' \
                         '[<level>{: <7}</level>]' \
                         '[<cyan>{}</cyan>.<cyan>{}</cyan>.<cyan>{}</cyan>]' \
                         + ros_node \
                         + period \
                         + ' <level>{}</level>'
            log_format = cls._colorize(log_format, level)   # 彩色化日志
        else:
            log_format = '[{}][{: <8}][{}.{}.{}.{}]{} {}'
        args = (cst_time, level) + caller_info + ('{}',)     # 用参数填充，但留下日志位{}
        return log_format.format(*args)

    @staticmethod
    def _truncate(msg, *args, **kwargs):
        """截断文本字符"""
        truncate = kwargs.get('truncate', 0)
        if type(truncate) is int and truncate > 0:
            if len(msg) > truncate + 15:
                msg = '{}......{}'.format(msg[:truncate], msg[-15:])
        return msg

    @classmethod
    def _throttle(cls, level, *args, **kwargs):
        """是否达成限流条件"""
        # 日志等级限流
        if cls._levels.index(level.upper()) < cls._level:   # 日志等级是否在屏蔽范围内
            return True
        # 时间间隔限流
        period = kwargs.get('period', 0)
        if type(period) in [int, float]:
            key = kwargs.get('key') or '.'.join(map(str, cls._get_caller_info(**kwargs)))
            if cls._throttle_time.get(key, 0) + period > time.time():
                return True
            else:
                cls._throttle_time[key] = time.time()
        return False

    @classmethod
    # @TimeitDecorator
    def _log(cls, level, *args, **kwargs):
        """打印日志
            :param args: Positional arguments.
            :param kwargs: Keyword arguments.
            :keyword silence: If silence is True, silence print.
            :keyword period: The number of periods to add.
            :keyword truncate: Whether to truncate the text.
            :keyword quiet: If quiet is True, silence print, but msg return.
            :return: None.
        """
        # 若正处于静默中/或正处于节流控制中：返回空字符串''
        if kwargs.pop('silence', False) or cls._throttle(level, *args, **kwargs):
            return ''
        timestack = kwargs.get('timestack', False)
        # 消息内容准备
        msg = ' '.join([arg.encode('utf-8') if str(type(arg)) == "<type 'unicode'>" else (json.dumps(arg) if type(arg) is dict else str(arg)) for arg in args])
        msg = cls._truncate(msg, *args, **kwargs)
        msg_formatted = cls._get_log_format(level, *args, **kwargs).format(msg)
        # 消息内容打印
        if not kwargs.pop('quiet', False):
            print(msg_formatted if kwargs.pop('mask_sensitive_str', cls.mask_sensitive_str) else Methods.mask_sensitive_str(msg_formatted))  # .replace('\033', '\\033'): 打印原始字符串，不带颜色
            sys.stdout.flush()  # 立即刷新出来print打印的日志

        return timestack and msg_formatted or msg

    @classmethod
    def success(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def debug(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def info(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def warning(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def error(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def critical(cls, *args, **kwargs):
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, **kwargs)

    @classmethod
    def exception(cls, *args, **kwargs):
        exc_info = kwargs.get('exc_info', sys.exc_info())
        e = kwargs.get('e', exc_info[1])
        key = "{}.{}.'{}'".format('.'.join(map(str, cls._get_caller_info(**kwargs))), type(e).__name__, e)
        args = ('\n' + ''.join(traceback.format_exception(*exc_info)), ) + args
        return cls._log(cls._get_frame().f_code.co_name.upper(), *args, key=key, period=1, **kwargs)

    @classmethod
    def log(cls, level, *args, **kwargs):
        """日志打印：提供统一入口
        :param level: 'INFO','WARNING'/True/False"""
        if type(level) is bool:
            level = {True: 'SUCCESS', False: 'ERROR'}.get(bool(level))
        elif type(level) is not str:
            level = 'INFO'
        if level.upper() not in cls._color_map_level.keys():
            return cls._log('INFO', level, *args, **kwargs)
        return cls._log(level.upper(), *args, **kwargs)


log = _Log
