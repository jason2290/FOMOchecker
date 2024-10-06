import csv
import requests
import json
from datetime import datetime
import os
import sys
import io

# 强制使用 UTF-8 编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 定义API的URL
url = "https://fullnode.mainnet.sui.io/"
# 定义请求头
headers = {
    'Content-Type': 'application/json'
}

# 定义要读取的CSV文件名称
csv_file = 'wallets.csv'

# 取得当前时间，并生成log文件名
current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
log_file = f'log_{current_time}.csv'
report_file = 'report.csv'
report_group_file = 'reportgroup.csv'

# 定义变量存储上次的数据
previous_balances = {}

# 检查是否有之前的log文件
last_log = None
for file in os.listdir():
    if file.startswith('log_') and file.endswith('.csv'):
        if not last_log or file > last_log:
            last_log = file

# 读取上一份log文件，存储SUI和FOMO余额
if last_log:
    with open(last_log, newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过第一行时间
        next(reader)  # 跳过header
        for row in reader:
            address = row[2]
            previous_sui_balance = float(row[3])
            previous_fomo_balance = float(row[4])
            previous_balances[address] = {
                "sui": previous_sui_balance,
                "fomo": previous_fomo_balance
            }

# 用来存储每个group的计算结果
group_totals = {}

# 打开CSV文件并读取内容，同时开启log.csv文件以写入
with open(csv_file, newline='', encoding='utf-8') as file, open(log_file, mode='w', newline='', encoding='utf-8') as log, open(report_file, mode='w', newline='', encoding='utf-8') as report:
    reader = csv.reader(file)
    log_writer = csv.writer(log)
    report_writer = csv.writer(report)

    # 写入log.csv的第一行时间
    log_writer.writerow([f"Log generated at: {current_time}"])
    
    # 写入log.csv的header
    log_writer.writerow(['Group', 'Name', 'Address', 'SUI Balance', 'FOMO Balance'])

    # 写入report.csv的header
    report_writer.writerow(['Group', 'Name', 'Address', 'SUI消耗', 'FOMO產量', 'FOMO(B)/SUI'])

    next(reader)  # 跳过header

    # 依次读取每一行
    for row in reader:
        group = row[0]   # 分组
        name = row[1]    # 钱包名
        address = row[2] # 地址

        # 查询SUI余额
        payload_sui = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "suix_getBalance",
            "params": [
                address,
                "0x2::sui::SUI"
            ]
        }
        response_sui = requests.post(url, headers=headers, data=json.dumps(payload_sui)).json()
        total_balance_sui = int(response_sui['result']['totalBalance']) / (10 ** 9)  # SUI退9位

        # 查询FOMO余额
        payload_fomo = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "suix_getBalance",
            "params": [
                address,
                "0xa340e3db1332c21f20f5c08bef0fa459e733575f9a7e2f5faca64f72cd5a54f2::fomo::FOMO"
            ]
        }
        response_fomo = requests.post(url, headers=headers, data=json.dumps(payload_fomo)).json()
        total_balance_fomo = int(response_fomo['result']['totalBalance']) / (10 ** 11)  # FOMO退11位

        # 输出结果到终端
        print(f"錢包名稱: {name}")
        print(f"地址: {address}")
        print(f"SUI餘額: {total_balance_sui:.9f} SUI")
        print(f"FOMO餘額: {total_balance_fomo:.12f} B FOMO")
        print("-" * 30)

        # 将结果写入log.csv
        log_writer.writerow([group, name, address, f"{total_balance_sui:.9f}", f"{total_balance_fomo:.12f}"])

        # 计算SUI和FOMO的变化
        if address in previous_balances:
            sui_spent = previous_balances[address]['sui'] - total_balance_sui
            fomo_gained = total_balance_fomo - previous_balances[address]['fomo']
        else:
            sui_spent = 0
            fomo_gained = 0

        # 计算FOMO成本 (FOMO Gained / SUI Spent)，如果SUI Spent为0，则成本为0
        if sui_spent > 0:
            fomo_cost = fomo_gained / sui_spent
        else:
            fomo_cost = 0

        # 将变化结果写入report.csv
        report_writer.writerow([group, name, address, f"{sui_spent:.9f}", f"{fomo_gained:.12f}", f"{fomo_cost:.12f}"])

        # 累加至group总计
        if group not in group_totals:
            group_totals[group] = {"sui_spent": 0, "fomo_gained": 0}
        
        group_totals[group]["sui_spent"] += sui_spent
        group_totals[group]["fomo_gained"] += fomo_gained

# 开启reportgroup.csv并写入group的统计结果
with open(report_group_file, mode='w', newline='', encoding='utf-8') as report_group:
    group_writer = csv.writer(report_group)
    # 写入header
    group_writer.writerow(['Group', 'SUI use', 'FOMO gain', 'FOMO(B)/SUI'])
    
    # 计算每个group的FOMO Cost并写入
    for group, totals in group_totals.items():
        sui_spent = totals["sui_spent"]
        fomo_gained = totals["fomo_gained"]
        
        if sui_spent > 0:
            fomo_cost = fomo_gained / sui_spent
        else:
            fomo_cost = 0
        
        group_writer.writerow([group, f"{sui_spent:.9f}", f"{fomo_gained:.12f}", f"{fomo_cost:.12f}"])

# 读取并打印 reportgroup.csv 的内容
with open(report_group_file, mode='r', encoding='utf-8') as report_group:
    reader = csv.reader(report_group)
    print("組別統計:")
    for row in reader:
        print(row)  # 打印每一行内容
