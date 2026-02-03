import time

from pylib.thread_pool import ThreadPool


class Main:
    @staticmethod
    def _func(*args):
        time.sleep(1)
        return args

    @staticmethod
    def run():
        threadpool = ThreadPool()
        rst = []
        for i in range(10):
            rst.append(threadpool.submit(Main._func, i))
        rst = [r.result() for r in rst]
        print(rst)


if __name__ == "__main__":
    Main().run()
