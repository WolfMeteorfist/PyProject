# coding=UTF-8
import os
import time
import threading
import shlex
from datetime import datetime
import subprocess
import log
from watchdog.observers import Observer
from FileEventHandler import EventHandler
import shutil

# 性能目标app
# 'launcher' ， 以;为分隔符
target_app = ('launcher',)

# 捕获时间
# 10分钟: 10 * 60 * 1000
capture_time = 10 * 60 * 1000

app_package_dict = {
    'launcher': 'com.aispeech.ccui.launcher',
    'speech': 'com.aispeech.ccui.speech',
    'kernel': 'com.aispeech.ccui.voice',
    'setting': 'com.aispeech.ccui.setting',
}

# 全局获取时间戳
TIME_STAMP = datetime.utcnow().strftime('%m-%d %H:%M:%S.%f')[:-3]
# 源数据目录
ORIGIN_DATA_DIR = f'{os.path.dirname(__file__)}/{TIME_STAMP}/origin_data'
# 解析结果目录
RESULT_DIR = f'{os.path.dirname(__file__)}/{TIME_STAMP}/result'

app_pid_dict: dict[str, str] = dict()


def make_dirs(file_full_path):
    (filepath, filename) = os.path.split(file_full_path)
    if not filepath:
        return
    os.makedirs(name=filepath, exist_ok=True)


class CaptureEventTask:
    # 内存信息存储目标全路径
    mem_result_file = None

    # cpu信息存储目标全路径
    cpu_usage_file = None

    # 当前目标应用
    app = None

    # 目标应用所对应进程id
    pid = None

    # 结束捕获标识，用于退出while循环
    end_captrue_flag = False

    def __init__(self, app: str) -> None:
        log.d("构造出" + app)
        self.mem_result_file = ORIGIN_DATA_DIR + os.sep + "mem_info" + os.sep + app
        self.cpu_usage_file = ORIGIN_DATA_DIR + os.sep + "cpu_info" + os.sep + app
        self.app = app

        self.pid = self.__get_pid()
        pass

    def __get_top_info(self):
        log.d(f"开始捕获{self.app}的top数据. 目标pid为:{self.pid}")
        threading.Thread(target=self.__file_observe).start()
        # 获取所有当前运行线程
        tidList = subprocess.Popen(
            f"adb shell top -H -b -d 1 -m 10 -p {self.pid}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        log.v("写入中" + '.' * 10)
        while not self.end_captrue_flag:
            # 之所以每次都要open file，是因为当前没有办法在只open一次的情况下让watch_dog观测到文件变化
            # 目前发现的问题就是只有在close时，watchDog才能接受到回调.
            file = open(self.cpu_usage_file, 'a')
            for line in tidList.stdout:
                if len(line.strip()) == 0:
                    continue
                file.write(str(line))
                file.flush()
        pass

    # # 内容变更回调，打点用
    # def __do_when_change(f):
    #     log.d("变化啦！！")
    #     f.write(datetime.utcnow().strftime('%m-%d %H:%M:%S.%f')[:-3] + '\n')
    #     f.close()
    #     pass

    # # watch_dog进行观测.原理也是select.
    # def __file_watchdog(self):
    #     log.i(f"开始观测文件:'{self.cpu_usage_file}'变化")
    #     event_handler = EventHandler(self.__do_when_change)
    #     observer = Observer()
    #     observer.schedule(event_handler, path=self.cpu_usage_file, recursive=True)
    #     observer.start()
    #     try:
    #         observer.join()
    #         pass
    #     except KeyboardInterrupt:
    #         observer.stop()

    def __file_observe(self):
        f = open(self.cpu_usage_file, 'a')
        pre_modify_time = None
        while True:
            if os.stat(self.cpu_usage_file).st_mtime != pre_modify_time:
                print("检测到变化，正在写入时间.")
                f.write(datetime.utcnow().strftime('%m-%d %H:%M:%S.%f')[:-3] + '\n')
                f.flush()
                pre_modify_time = os.stat(self.cpu_usage_file).st_mtime
            time.sleep(0.5)
        pass

    def __get_mem_info(self):
        with open(self.mem_result_file, 'w') as f:
            while not self.end_captrue_flag:
                statm = subprocess.run(
                    'adb shell cat /proc/' + self.pid + '/statm',
                    shell=True,
                    capture_output=True,
                    encoding='utf-8',
                ).stdout
                timestamp = datetime.utcnow().strftime('%m-%d %H:%M:%S.%f')[:-3]
                time.sleep(1)
                f.write(timestamp + '\n')
                f.write(statm)
                f.flush()
                pass
            pass
        pass

    # 获取app对应的pid
    def __get_pid(self) -> str:
        global app_pid_dict
        pid = app_pid_dict.get(self.app, None)
        if pid:
            return pid
        package = app_package_dict.get(self.app, None)
        if not package:
            log.e(self.app + "未找到对应包名.")
            os._exit(-1)
        log.d(f"对应包名：{package}")
        pid = (
            subprocess.run(
                'adb shell ps -ef | grep -v grep | grep '
                + self.app
                + '| awk \'{print $2}\'',
                shell=True,
                capture_output=True,
            )
            .stdout.decode()
            .strip()
        )
        log.d(f"查找到{self.app}对应的pid:{pid}.")
        app_pid_dict[self.app] = pid
        return pid

    def start_capture(self):
        # 创建文件夹
        make_dirs(self.mem_result_file)
        make_dirs(self.cpu_usage_file)
        # 开启线程捕获cpu数据
        top_t = threading.Thread(target=self.__get_top_info)
        # 开启线程捕获mem数据
        mem_t = threading.Thread(target=self.__get_mem_info)
        top_t.start()
        mem_t.start()
        top_t.join()
        mem_t.join()
        # 进行观测，若接收到输入，终止捕获并进行数据分析

        pass

    def end_and_analyze(self):
        pass

    pass


logCaptureLock = threading.Lock()


def get_sys_meminfo():
    pass


def get_cpu_usage():
    pass


# 分析meminfo
def analyze_meminfo(mem_file_path: str):
    pass


# 分析cpu
def analyze_cpuinfo(top_file_path: str):
    pass


def startGetLog():
    # 清空日志

    subprocess.run(shlex.split("adb logcat -c"))
    log_file = f'{ORIGIN_DATA_DIR}{os.sep}log_file.log'
    make_dirs(log_file)
    with open(log_file, 'w') as f:
        process = subprocess.Popen(
            ['adb', 'shell', 'logcat', 'V', '-v', 'threadtime'], stdout=f
        )
        log.d("我在等待Cpu数据捕获结束！")
        logCaptureLock.acquire()
        process.terminate()
        pass
    pass


if __name__ == '__main__':
    # startGetLog()
    for app in target_app:
        capture_task = CaptureEventTask(app)
        capture_task.start_capture()
    pass
