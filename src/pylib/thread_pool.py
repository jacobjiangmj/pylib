# coding: utf-8
import sys
import time
import uuid
import atexit
import traceback
import threading
import multiprocessing

from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor

from pylib.log import log
from pylib.methods import Methods


class ThreadPool:
    max_thread_size = 8 * multiprocessing.cpu_count()
    executor = _ThreadPoolExecutor(max_workers=max_thread_size, thread_name_prefix='')
    # py2: 没有Semaphore所以用整形；py3: 用它而不是整形：防止多线程同时修改导致覆盖
    _activated_threads = threading.Semaphore(0) if sys.version_info.major == 3 else 0
    _silence = True    # debug日志是否静默
    _silence_exception = True    # debug日志是否静默
    _lock = threading.Lock()

    def __init__(self, max_thread_size=None, thread_name_prefix='', **kwargs):
        max_thread_size = max_thread_size if max_thread_size else 8 * multiprocessing.cpu_count()
        self.max_thread_size = max_thread_size
        self._silence = kwargs.get('silence') or self._silence
        self._silence_exception = kwargs.get('silence_exception') or self._silence_exception
        self.executor = _ThreadPoolExecutor(max_workers=self.max_thread_size, thread_name_prefix=thread_name_prefix)
        atexit.register(self._shutdown, wait=False)
        self.executor_name = f"{str(uuid.uuid4())[:8]}.{thread_name_prefix}.{Methods.get_stack_funcs(3).lstrip('.')}"
        log.info('初始化多线程', Methods.get_stack_funcs(5), silence='runserver' not in Methods.read_args())

    def __del__(self):
        if not self._silence:
            print('多线程解构', Methods.get_stack_funcs(5), self.executor_name, f"当前正在运行的线程数量：{self.get_activated_threads()}")

    def _shutdown(self, wait=False):
        log.warning(f"强制退出线程并关闭线程池: {self.executor_name}。当前正在运行的线程数量：{self.get_activated_threads()}",
                    silence='runserver' not in Methods.read_args())
        self.executor.shutdown(wait=wait)

    def get_activated_threads(self):
        """获取线程池中正在运行的线程数"""
        if sys.version_info.major == 3:
            return self._activated_threads.__getattribute__('_value')
        else:
            return self._activated_threads

    @classmethod
    def _handle_exception(cls, future):
        """线程执行异常处理"""
        try:
            future.result()  # 尝试获取执行结果，如果有异常会在这里抛出
        except Exception as e:
            if not cls._silence_exception:
                traceback.print_exception(type(e), e, sys.exc_info()[2])

    def _wrapper_function(self, submitted_function, *args, **kwargs):
        """将方法包装一层计数"""
        with self._lock:
            # 0. 参数准备
            silence = kwargs.pop('silence', False) or self._silence
            if sys.version_info.major == 3:
                self._activated_threads.release()  # 增加计数器
            else:
                self._activated_threads += 1
            if hasattr(submitted_function, '__self__'):
                method_full_name = '{}.{}.{}'.format(
                    submitted_function.__self__.__class__.__module__,
                    submitted_function.__self__.__class__.__name__,
                    submitted_function.__name__)
            else:
                method_full_name = '{}.{}.{}'.format(
                    submitted_function.__class__.__module__,
                    submitted_function.__class__.__name__,
                    submitted_function.__name__)
            level = 'INFO' if self.get_activated_threads() < 5 else 'WARNING'
            log.log(level, 'thread submit: {}/{}, {}, thread_id: {}'.format(
                self.get_activated_threads(), self.max_thread_size, method_full_name, threading.current_thread().ident),
                      *args, silence=silence, **kwargs)
        try:
            return submitted_function(*args, **kwargs)
        finally:
            with self._lock:
                if sys.version_info.major == 3:
                    self._activated_threads.acquire()  # 任务完成后减少计数器
                else:
                    self._activated_threads -= 1
                log.log('SUCCESS', 'thread complete: {}/{}, {}, thread_id: {}'.format(
                    self.get_activated_threads(), self.max_thread_size, method_full_name, threading.current_thread().ident),
                          *args, silence=silence, **kwargs)

    def _submit(self, *args, **kwargs):
        future = self.executor.submit(self._wrapper_function, *args, **kwargs)
        future.add_done_callback(self._handle_exception)
        return future

    @staticmethod
    def _submit_delay(*args, **kwargs):
        """延迟seconds秒后再执行传上来的方法
        py3.0才加的keyword-only，所以这里暂时不使用keyword-only
        无论哪种方法，都会占用一个关键词，这里选择seconds"""
        time.sleep(kwargs.pop('seconds', 0))
        return args[0](*(args[1:]), **kwargs)

    def submit_delay(self, *args, **kwargs):
        """入口：延迟seconds秒后再执行传上来的方法"""
        return self.submit(self._submit_delay, *args, **kwargs)

    def submit(self, *args, **kwargs):
        """提交到新线程中
        占用关键词drop_waiting"""
        if kwargs.pop('drop_waiting', False) and self.get_activated_threads() >= self.max_thread_size:
            return None
        return self._submit(*args, **kwargs)

    @classmethod
    def submit_static(cls, *args, **kwargs):
        """提交到新线程中（类方法）"""
        future = cls.executor.submit(args[0], *args[1:], **kwargs)
        future.add_done_callback(cls._handle_exception)
        return future

    @classmethod
    def set_daemon(cls, target, *args, **kwargs):
        """设置线程为守护线程
        该方法支持回调函数
        当所有非守护线程都结束时，守护线程也会随之结束；避免出现僵尸线程的情况
        使用方法：ThreadPool.set_daemon(KeyboardListener().listen_input, self.keyboard_callback)
        self.keyboard_callback为回调函数，在listen_input中自行调用"""
        keyboard_thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        keyboard_thread.setDaemon(True)
        keyboard_thread.start()

    @classmethod
    def waiting_for_complete_cls(cls, thread_pool_executor=None):
        if thread_pool_executor is None:
            return cls.executor.shutdown(wait=True)
        else:
            return thread_pool_executor.shutdown(wait=True)

    def waiting_for_complete(self, wait=True):
        return self.executor.shutdown(wait=wait)

    @classmethod
    def waiting_for_complete_static(cls, wait=True):
        return cls.executor.shutdown(wait=wait)

    def shutdown(self, cancel_futures=True):
        """关闭线程
        :params cancel_futures: True: 取消队列中的任务"""
        self.executor.shutdown(cancel_futures=cancel_futures)     # 关闭线程并取消队列中的任务
