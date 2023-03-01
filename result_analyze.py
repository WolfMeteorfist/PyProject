import pandas as pd
import fileinput
import re
import os
import log
import numpy
import subprocess

# 内存数据解析
def mem_analyze(app, target_file, output_dir):
    time_stamp = []
    resident_set_size = []

    for line in fileinput.input(target_file):
        if re.match(r'^\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}.\d+', line):
            time_stamp.append(line)
        else:
            resident_set_size.append(int(line.split()[1]) * 4 / 1024)
            pass

    time_stamp += ('最大值',)
    resident_set_size.append(numpy.max(resident_set_size))
    time_stamp += ('最小值',)
    resident_set_size.append(numpy.min(resident_set_size))
    time_stamp += ('平均值',)
    resident_set_size.append(numpy.average(resident_set_size))
    time_stamp += ('中位数',)
    resident_set_size.append(numpy.median(resident_set_size))

    ps = pd.Series(resident_set_size, index=time_stamp)
    log.v("最大值:"+str(ps.max()))
    log.v("最小值:"+str(ps.min()))
    mem_result_file_path = f'{output_dir}em_result.xlsx'
    if not os.path.exists(mem_result_file_path):
        ps.to_excel(mem_result_file_path, sheet_name=app, index=True)
    else:
        log.v("mem_result.xlsx 文件已存在, 直接写入.")
        writer = pd.ExcelWriter(mem_result_file_path,
                                mode='a', engine='openpyxl')
        # 写入Excel表格
        ps.to_excel(writer, sheet_name=app, index=True)
        # 保存Excel表格
        writer.save()
        pass
    pass

# cpu数据分析
def cpu_analyze(app, pid, target_file, output_dir):
    # 线程cpu数据集合
    thread_map: dict[str, list[str]] = {}
    time_stamp_index = []
    cur_row_length = 1
    can_skip = False
    for line in fileinput.input(target_file):
        if re.match(r'^\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}.\d+$', line):
            # 时间行
            cur_row_length += 1
            time_stamp_index.append(line)
            # 新的一轮即将开始
            can_skip = False
            pass
        elif can_skip:
            # 由于是CPU排序，若前边的是0，后边则均为0
            continue
        elif re.match(r'^\s{0,3}\d+ .*', line):
            filter_process, _ = re.search(pattern=r'(.*)\s(\w+.\w+.\w+.*)$', string=line).groups()
            _, t_name = re.search(pattern=r'.*?(\d+:\d+.\d+)\s(.*)$',string= filter_process).groups()
            key = f'{t_name}\n({line.split()[0]})'
            cpu = line.split()[8]
            if float(cpu) == 0:
                can_skip = True
                continue
            
            if key not in thread_map:
                # 若从来都木有数据则，补齐长度
                thread_map[key] = list()
            thread_map[key].extend([0.0] * (cur_row_length -len(thread_map[key]) - 1))
            thread_map[key].append(cpu)
            pass
        pass
    log.d(f"{app}的cpu解析完成，正在生成excel表格.")
    
    # 补齐
    # 创建DataFrame并将长度不足的Series填充为NaN
    for item in thread_map.items():
        item[1].extend([0.0]* (cur_row_length -len(item[1]) - 1))
        pass
    df = pd.DataFrame(thread_map, index=time_stamp_index)

    # 输出为Excel文件
    df.to_excel(f'{output_dir}cpu_usage.xlsx', sheet_name='线程CPU占用', index=True)
    
    # 生成运行时间快照
    tid_list = []
    time_list = []
    thread_name_list = []
    top_process = subprocess.run(f'adb shell top -H -k %CPU -s 11 -b -n 1 -p  {pid}', shell=True, capture_output=True)
    for line in top_process.stdout.decode().splitlines():
        if re.match(r'^\s{0,3}\d+ .*', line):
            tid,time,name =re.search(r'^\s{0,3}(\d+)\s.*(\d+:\d+.\d+)\s(.*)$', line).groups()
            tid_list.append(tid)
            time_list.append(time)
            thread_name_list.append(name)
            pass
        
    cpu_snap = {
        "ThreadId" : tid_list,
        "RunTime" : time_list,
        "ThreadName" : thread_name_list
    }
    
    writer = pd.ExcelWriter(f'{output_dir}cpu_usage.xlsx', mode='a', engine='openpyxl')
    df = pd.DataFrame(cpu_snap)
    df.to_excel(writer, sheet_name='运行时间快照', index=False)
    writer.save()
    
    pass