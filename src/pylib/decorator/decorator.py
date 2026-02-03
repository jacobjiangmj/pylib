import types
import functools


class Decorator(object):
    """
    装饰器基类，无直接功能（为兼容py2.7，(object)不可删）
        使用方法：
            无参注解：@Decorator
            有参注解：@Decorator()   # 且会先声明，后调用，调用时没有instance和owner，唯一id从instance改成从func中读取

    py2.7
        静态方法（被@staticmethod装饰）：没有owner，没有instance
        类方法（被@classmethod装饰）：没有owner，有instance
        实例方法：有owner，有instance
    py3.6
        静态方法（被@staticmethod装饰）：没有owner，没有instance
        类方法（被@classmethod装饰）：没有owner，有instance
        实例方法：有owner，有instance

    若同时使用@staticmethod注解
    或用@classmethod注解时，它们应当先于@Decorator注解
    """

    def __init__(self, *args, **kwargs):
        """注解时触发，args和kwargs为可接收有参注解
        仅当对类使用@Decorator()注解时args长度才为0"""
        self.callable_obj = args[0] if len(args) > 0 else None  # 读取被注解的对象

    def __getattr__(self, item):
        """读取被注解对象属性时触发
        当尝试访问不存在的属性时使用
        目前仅用于读取同时注解了静态方法的方法名时，解决无法读取到的问题"""
        return getattr(self.callable_obj, item)

    def __get__(self, instance, owner):
        """以get为入口：
        实例化方法、类方法（被@classmethod装饰）
        被调用时"""
        return self._get_wrapper(instance, owner)

    def __call__(self, *args, **kwargs):
        """以call为入口：
        静态方法（被@staticmethod装饰）
        实例方法，以@Decorator()注解时
        类，以@Decorator或以@Decorator()注解时（类以@Decorator()注解时，表示以执行实例化）
        被调用时"""
        if not self.callable_obj and len(args) > 0 and (self._is_class(args[0]) or self._is_function(args[0])):
            self.callable_obj = self.callable_obj or args[0]
            args = args[1:]
        return self._get_wrapper()(*args, **kwargs)

    def _get_key(self, instance=None, owner=None, *args, **kwargs):
        """获取被注解方法的唯一key标志符"""
        if owner is None:   # 装饰静态方法时，没有owner
            key = getattr(self.callable_obj, '__qualname__', self.callable_obj.__name__)
        else:
            key = "{}.{}.{}".format(owner.__module__, owner.__name__, self.callable_obj.__name__)

        if instance is not None:
            key += ".{}(instance_id)".format(hex(id(instance)))
        elif self._is_class(self.callable_obj):
            key += ".{}(class_id)".format(hex(id(self.callable_obj)))
        else:
            key += ".{}(func_id)".format(hex(id(self.callable_obj)))

        return key

    @staticmethod
    def _is_class(obj):
        """判断是否是类"""
        return isinstance(obj, (type, getattr(types, 'ClassType', type)))

    @staticmethod
    def _is_function(obj):
        """判断是否是函数"""
        return isinstance(obj,
                          (types.FunctionType, types.BuiltinFunctionType, types.MethodType, types.BuiltinMethodType))

    def _get_wrapper(self, instance=None, owner=None):
        """获取装饰器函数"""
        @functools.wraps(self.callable_obj)
        def wrapper(*args, **kwargs):
            # 有参类装饰时，在这里赋值callable_obj
            if len(args) > 0 and self._is_class(args[0]):
                self.callable_obj = args[0]
                args = args[1:]

            # 运行
            try:
                args = (instance,) + args if instance is not None else args     # 实例方法时，要将实例插入元组args首位
                return self.callable_obj(*args, **kwargs)
            finally:
                pass
        return wrapper
