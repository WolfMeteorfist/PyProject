# coding=UTF-8
import fileinput
import os
import shlex
import subprocess
import threading
import time
import re
from datetime import datetime
import costTime
import log

# 识别使用线程
ASR_WT = "lite-t-LocalAsr lite-t-VadKerne"

# 唤醒使用线程
WAKE_WT = "lite-t-WakeupKernel"

# 本地语义使用线程
LOCAL_SEMATIC_WT = "lite-t-LocalSem"

# 本地TTS使用线程
LOCAL_TTS_WT = "lite-t-LTtsKern"

# 数据抓取时间
CAPTURE_TIME = 30 * 60

ASR_START_TAG = "AI-dms_node: vadEnd..."
ASR_END_TAG = "will feed nlu"

SEMATIC_START_TAG = "will feed nlu"
SEMATIC_END_TAG = "feed input text ldm"

TTS_START_TAG = "AI-tts_TextProxy-STAMP: [TTS.START]"
TTS_END_TAG = "AI-tts_TextProxy-STAMP: [TTS.END]"

# 识别阶段tag
ASR_TAG_REGEX = "grep -E \"(AI-dms_node: vadEnd...|will feed nlu)\""

# 语义阶段
SEMATIC_TAG_REGEX = "grep -E \"(will feed nlu|feed input text ldm)\""

# 合成阶段
TTS_TAG_REGEX = "grep -E \"(AI-tts_TextProxy-STAMP: \[TTS.START\]|AI-tts_TextProxy-STAMP: \[TTS.END\])\""

log_file_path = None

result_target_dir = None

file_name_suffix = None

origin_data_dir_path = f"{os.path.dirname(__file__)}{os.sep}origin_data"

# 分析CPU使用锁，用于logcat等待cpu数据获取结束
cpuCaptureLock = threading.Lock()

# 本次获取的CPU_USAGE文件
cpu_file = None

# 字典
thread_dict_file = dict()

# 分析线程锁，用于等待日志准备完毕后进行
annalyzeLock = threading.Lock()

FILER_ZERO_USAGE = True


def getWorkThreadCpuUsage(path: str, target_wt: str, fileName: str = None):
    print(f"开始解析识别线程. {target_wt}")
    wtList = target_wt.split(sep=' ')
    if fileName == None:
        fileName = target_wt

    target_file = f"{result_target_dir}{os.sep}{fileName}_CPU_USAGE"
    # 不进行时间点判断，只过滤0值
    target_file_all_filter_zero = (
        f"{result_target_dir}{os.sep}{fileName}_CPU_USAGE_FILTER_ZERO"
    )
    thread_dict_file[fileName] = target_file

    dir_exist = os.path.exists(result_target_dir)
    if dir_exist == False:
        os.makedirs(result_target_dir)
        pass
    f_filer_zero = open(f"{target_file_all_filter_zero}", 'w')
    with open(f"{target_file}", 'w') as f:
        f.truncate()
        for line in fileinput.input(path):
            contain = None
            if re.match(r"(^.*\d+:\d+:\d+\.\d+$)", line):
                f.write(line)
                continue
            for w in wtList:
                if line.find(w) != -1:
                    contain = True
                    break
            if contain == True:
                cpuUsage = line.split()[8]
                f.write(
                    cpuUsage + " " +
                    line.split()[-3] + " " + line.split()[-2] + "\n"
                )
                if not FILER_ZERO_USAGE or not cpuUsage == '0.0':
                    f_filer_zero.write(
                        cpuUsage
                        + " "
                        + line.split()[-3]
                        + " "
                        + line.split()[-2]
                        + "\n"
                    )
                    pass
                pass
            pass
    print("完成线程识别...")
    f_filer_zero.close()
    pass


def startGetCpuUsage():
    print("开始捕获Cpu占用数据,请勿退出。")
    process = subprocess.Popen(
        "adb shell ps -ef | grep voice | grep -v grep | awk '{print $2}'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    voicePid = process.stdout.readline().decode()
    print("Voice进程ID：" + voicePid)

    if not voicePid:
        log.e("请确认是否安装voice应用.")
        os._exit(-1)

    startTime = datetime.now()

    global cpu_file

    with open(cpu_file, 'w') as f:
        f.truncate()
        while (datetime.now() - startTime).seconds <= (
            CAPTURE_TIME
        ) and captureEnd == False:
            cpuUsage = subprocess.Popen(
                shlex.split("adb shell top -H -n 1 -b -p " + voicePid),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            captureTime = subprocess.run(
                shlex.split(
                    'adb shell date +"%m-%d\ %H:%M:%S.%N" | cut -b 1-18'),
                capture_output=True,
            )
            timeTag = captureTime.stdout.decode()
            out_info = cpuUsage.stdout.readlines()
            f.write(f"{timeTag}")
            for line in out_info:
                f.write(line.decode("unicode-escape"))
                pass
            pass
    print("Cpu数据捕获完成,可执行数据过滤。")
    cpuCaptureLock.release()
    pass


def startGetLog():
    # 清空日志
    subprocess.run(shlex.split("adb logcat -c"))
    with open(f'{log_file_path}', 'w') as f:
        process = subprocess.Popen(
            ['adb', 'shell', 'logcat', 'V', '-v', 'threadtime'], stdout=f
        )
        print("我在等待Cpu数据捕获结束！")
        cpuCaptureLock.acquire()
        process.terminate()
        cpuCaptureLock.release()
        annalyzeLock.release()
        pass
    pass


def checkNeedWait():
    global captureEnd
    cmd = input("输入任意键可提前结束日志抓取!\n")
    captureEnd = True
    pass


class TimeRange:
    def __init__(self, start=None, end=None) -> None:
        self.start = start
        self.end = end
        pass

    def __get_time_stamp(self, valid_time):
        dd = datetime.strptime(valid_time, '%m-%d %H:%M:%S.%f')
        ts = int(time.mktime(dd.timetuple()) *
                 1000.0 + (dd.microsecond / 1000.0))
        return ts

    # 0 范围内 -1，早于。 1, 晚于
    def compareTime(self, _time):
        if _time and self.start and self.end:
            _time_stamp = self.__get_time_stamp(_time)
            start_time_stamp = self.__get_time_stamp(self.start)
            end_time_stamp = self.__get_time_stamp(self.end)
            if int(_time_stamp) >= int(start_time_stamp) and int(_time_stamp) <= int(
                end_time_stamp
            ):
                return 0
            elif int(_time_stamp) < int(start_time_stamp):
                return -1
            else:
                return 1
        else:
            return None


asr_time_list: list[TimeRange] = list()
sematic_time_list: list[TimeRange] = list()
tts_time_list: list[TimeRange] = list()

time_dict: dict[str: list[TimeRange]] = dict()
time_dict["ASR"] = asr_time_list
time_dict["SEMATIC"] = sematic_time_list
time_dict["TTS"] = tts_time_list


def getLogTime(regex: str, startTag: str, endTag: str, list: list[TimeRange] = None):
    print("StartGetLogTime.")
    egrepProcess = subprocess.run(
        shlex.split(f"{regex} {log_file_path}"), capture_output=True
    )
    lines = egrepProcess.stdout.decode().splitlines()
    tr = None
    for line in lines:
        if line.find(startTag) != -1:
            tr = TimeRange()
            tr.start = line.split(' ')[0] + ' ' + line.split(' ')[1]
        if line.find(endTag) != -1:
            if tr:
                tr.end = line.split(' ')[0] + ' ' + line.split(' ')[1]
                if list != None:
                    list.append(tr)
                    print("发现匹配项目，添加进列表.")
                tr = None
                pass
            pass
        pass

    print("解析时间 {} Tag完成.".format(regex))
    pass


def getValidData(target: str):
    listIndex = 0  # timeRange下标
    validData = False  # 是否为有效数据
    time_list: list = time_dict[target]
    # 如果下标越界，直接返回
    if time_list.__len__() == 0:
        return
    timeRange: TimeRange = time_list[listIndex]
    targetFile = thread_dict_file[target]
    with open(targetFile, 'r') as f:
        # 当读取到的时间早于timeRange的start.则读取到下一行的时间
        # 当读取到的时间处于timeRange的范围内，设置validData为True，则为有效数据。
        # 当读取到的时间晚于timeRange的end.则遍历timeRange的下一个节点。
        line = f.readline().strip('\n')

        asrResultFile = open(
            f"{result_target_dir}{os.sep}{target}_FILTER", 'w')

        print(
            "本次查找{}, 起始时间: {}. 结束时间: {}.".format(
                target, timeRange.start, timeRange.end)
        )
        while line and listIndex < time_list.__len__():
            isTimeLine = re.match(r"(^\d+-\d+\s{1}\d+:\d+:\d+\.\d+$)", line)
            timeRange = time_list[listIndex]
            if isTimeLine:
                timeCompare = timeRange.compareTime(line)
                if timeCompare == 0:
                    validData = True
                elif timeCompare == -1:
                    # 早于timeRanage.start. 移动line
                    pass
                else:
                    # 晚于timeRange.end. 移动listIndex
                    listIndex += 1
                    if listIndex < time_list.__len__():
                        print(
                            "下次查找{}, 起始时间: {}. 结束时间: {}.".format(
                                target,
                                time_list[listIndex].start,
                                time_list[listIndex].end,
                            )
                        )
                    pass
                pass
            else:
                if validData:
                    # 有效数据，添加到列表，并遍历下一条
                    # 增加一个判断，若cpu占用为0，则不统计
                    if not isZeroCpuUsage(line):
                        asrResultFile.write(line + '\n')
                    pass
                pass
            line = f.readline().strip('\n')
            pass
        asrResultFile.close()
        pass
    print("有效cpu数据写入完成.")
    pass


def isNumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def isZeroCpuUsage(line: str) -> bool:
    time = line.split(' ')[0]
    if isNumber(time):
        return float(time) == 0
    else:
        return None


if __name__ == '__main__':
    print("程序开始.")
    captureEnd = False
    file_path = os.path.dirname(__file__)

    file_name_suffix = datetime.now().strftime("%m-%d-%H:%M:%S")
    origin_data_dir_path = f"{origin_data_dir_path}{os.sep}{file_name_suffix}"

    cpu_file = f"{origin_data_dir_path}{os.sep}cpu_usage.log"
    result_target_dir = (
        f"{os.path.dirname(__file__)}{os.sep}result{os.sep}{file_name_suffix}"
    )
    log_file_path = f"{origin_data_dir_path}{os.sep}log_file.log"

    cpuCaptureLock.acquire()
    annalyzeLock.acquire()
    if not os.path.isdir(origin_data_dir_path):
        os.makedirs(origin_data_dir_path)

    getCpuThread = threading.Thread(target=startGetCpuUsage)
    getCpuThread.start()
    getLog = threading.Thread(target=startGetLog)
    getLog.start()
    checkNeedWait()
    annalyzeLock.acquire()
    print("日志获取完毕，开始分析日志...")
    getLogTime(ASR_TAG_REGEX, ASR_START_TAG, ASR_END_TAG, asr_time_list)
    getLogTime(SEMATIC_TAG_REGEX, SEMATIC_START_TAG,
               SEMATIC_END_TAG, sematic_time_list)
    getLogTime(TTS_TAG_REGEX, TTS_START_TAG, TTS_END_TAG, tts_time_list)
    # print("完成时间节点截取！")
    getWorkThreadCpuUsage(cpu_file, ASR_WT, "ASR")
    getWorkThreadCpuUsage(cpu_file, LOCAL_SEMATIC_WT, "SEMATIC")
    getWorkThreadCpuUsage(cpu_file, LOCAL_TTS_WT, "TTS")
    # getValidDataJustFilerZeroUsage("ASR")
    # getValidDataJustFilerZeroUsage("SEMATIC")
    # getValidDataJustFilerZeroUsage("TTS")
    getValidData("ASR")
    getValidData("SEMATIC")
    getValidData("TTS")

    costTime.getCostTime(result_target_dir, log_file_path)
