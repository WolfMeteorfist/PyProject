import os
import shlex
import subprocess
import sys
import log
import re
import pandas
import numpy

log.LOG_LEVEL = 2

COST_TIME_TAG = "CostTime-COST: costTime"

try:
    log_file_path = sys.argv[1]
except IndexError:
    log.i("只有一个参数.")
    # 只有一个参数
    pass

result_dir_path = f"{os.path.dirname(__file__)}{os.sep}result"


def getCostTime(resultDir: str, logFilePath: str):
    global result_dir_path
    if resultDir:
        result_dir_path = resultDir

    log.d("获取耗时日志： 目标文件：" + logFilePath)
    if not os.path.exists(logFilePath):
        log.e("ERROR:文件不存在，请检查！")
        return

    process = subprocess.run(
        'grep -E "(CostTime-COST:  costTime|local iot,api:|finish iot control.|feed input.*\"errId\".*)" {0} | grep -v -E "(asrResult.*呜呜)"'.format(logFilePath), capture_output=True)
    costTimeLog = process.stdout.decode('unicode_escape').splitlines()
    log.d("总共找到了:{0}行".format(costTimeLog.__len__()))

    if not os.path.exists(result_dir_path):
        log.d("创建result文件夹")
        os.makedirs(result_dir_path)
    result_file_path = f"{result_dir_path}{os.sep}cost_time.log"
    result_file = open(result_file_path, 'w')

    for line in costTimeLog:
        searchResult = re.search(
            r"(costTime:ttsStart -> ttsEnd =.*?ms/word)", line)
        if searchResult:
            result_file.write(searchResult.group()+'\n')

        searchResult = re.search(
            r"(costTime.*?\d+|^.*local iot,api:.*|^.*finish iot control.*|feed input.*\"errId\".*)", line)
        if searchResult:
            result_file.write(searchResult.group()+'\n')
        pass

# 这个忘记了！！！！！导致在执行filterTimeToExcel时，文件还未写入！！！麻了革八字
    result_file.close()
    filterTimeToExcel(result_file_path)
    pass


timeTagList = ['vadEnd -> asrResult',
               'asrResult -> dmOutput', 'ttsStart -> playStart']


def filterTimeToExcel(costTimeLogPath: str):
    asrTimeList = list()
    sematicTimeList = list()
    ttsTimeList = list()
    invaild = False
    with open(costTimeLogPath, 'r') as f:
        line = f.readline().strip('\n')
        while line:
            # 计算耗时，包括平均耗时，最大耗时，最短耗时
            if re.match(rf".*vadEnd -> asrResult.*", line):
                asrTimeList.append(
                    int(re.search(r"\d+", line).group().strip()))
            elif re.match(rf".*asrResult -> dmOutput.*", line):
                if not invaild:
                    sematicTimeList.append(
                        int(re.search(r"\d+", line).group().strip()))
                else:
                    invaild = False
            elif re.match(r"feed input.*\"errId\".*", line):
                invaild = True
            elif re.match(r".*ttsStart -> playStart.*", line):
                ttsTimeList.append(
                    int(re.search(r"\d+", line).group().strip()))
            else:
                # 略过
                pass
            pass
            line = f.readline().strip('\n')
        pass

    log.v("vadEnd->asrResult耗时信息===> 平均耗时: {}. 最短耗时: {}. 最长耗时: {}".format(
        numpy.average(asrTimeList), numpy.min(asrTimeList), numpy.max(asrTimeList)))
    log.v("asrResult->dmOutput耗时信息===> 平均耗时: {}. 最短耗时: {}. 最长耗时: {}".format(
        numpy.average(sematicTimeList), numpy.min(sematicTimeList), numpy.max(sematicTimeList)))
    log.v("ttsStart->playStart耗时信息===> 平均耗时: {}. 最短耗时: {}. 最长耗时: {}".format(
        numpy.average(ttsTimeList), numpy.min(ttsTimeList), numpy.max(ttsTimeList)))

    result = {
        'vadEnd->asrResult': asrTimeList,
        'asrResult->dmOutput': sematicTimeList,
        'ttsStart->playStart': ttsTimeList
    }
    # pandas.DataFrame(result).to_excel(f'{result_dir_path}{os.sep}result.xlsx', index=False)
    # global result_dir_path
    df2 = pandas.DataFrame(pandas.DataFrame.from_dict(
        result, orient='index').values.T, columns=list(result.keys()))
    stats = pandas.DataFrame([
        [numpy.max(asrTimeList), numpy.max(
            sematicTimeList), numpy.max(ttsTimeList)],
        [numpy.average(asrTimeList), numpy.average(
            sematicTimeList), numpy.average(ttsTimeList)],
        [numpy.min(asrTimeList), numpy.min(sematicTimeList), numpy.min(ttsTimeList)]], columns=list(result.keys()))
    # 将新的一行添加到原始数据框中
    df2 = df2.append(stats)
    df2.to_excel(f'{result_dir_path}{os.sep}result.xlsx',
                 startcol=1, index=False)
    pass


# getCostTime("/Volumes/superdisk/python_project/result/02-16-12:41:39",
#             "/Volumes/superdisk/python_project/origin_data/02-16-12:41:39/log_file.log")

# 提示框！
# os.system('osascript -e \'display notification "%s" with title "" subtitle "" \'' % 'asdasdsa')
