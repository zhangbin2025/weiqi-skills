#!/bin/bash
# 云比赛网围棋赛事监控脚本
# 每天获取广东省围棋比赛，检测新增项目

WORK_DIR="/root/.openclaw/workspace/yunbisai"
DATA_DIR="$WORK_DIR/data"
LOG_FILE="$WORK_DIR/monitor.log"
EMAIL_SCRIPT="/root/.openclaw/workspace/send_email.py"
TO_EMAIL="195021300@qq.com"

# ===== 性能计时工具 =====
declare -A TIMINGS
TIMER_START=$(date +%s.%N)

# 计时开始
start_timer() {
    echo $(date +%s.%N)
}

# 计时结束并记录
end_timer() {
    local name="$1"
    local start_time="$2"
    local end_time=$(date +%s.%N)
    local elapsed=$(echo "$end_time - $start_time" | bc)
    TIMINGS["$name"]=$elapsed
}

# 格式化性能报告
format_perf_report() {
    local total_elapsed=$(echo "$(date +%s.%N) - $TIMER_START" | bc)
    local report="\n==================================================\n⏱️  性能计时报告\n=================================================="
    local step_total=0
    
    for key in "${!TIMINGS[@]}"; do
        local val=${TIMINGS[$key]}
        step_total=$(echo "$step_total + $val" | bc)
        report="$report\n  $(printf "%-25s" "$key") : $(printf "%8.3f" $val)s"
    done
    
    report="$report\n--------------------------------------------------"
    report="$report\n  $(printf "%-25s" "步骤累计") : $(printf "%8.3f" $step_total)s"
    report="$report\n  $(printf "%-25s" "总耗时") : $(printf "%8.3f" $total_elapsed)s"
    report="$report\n=================================================="
    echo -e "$report"
}

# 创建目录
mkdir -p "$DATA_DIR"

# 获取当前日期
TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -d "yesterday" +%Y%m%d 2>/dev/null || date -v-1d +%Y%m%d)

# 今天的数据文件
TODAY_FILE="$DATA_DIR/events_$TODAY.json"
YESTERDAY_FILE="$DATA_DIR/events_$YESTERDAY.json"

# 获取所有比赛数据（支持多页）
fetch_all_events() {
    local output_file=$1
    local page=1
    local total_pages=1
    local temp_file=$(mktemp)
    
    echo "[]" > "$temp_file"
    
    while [ "$page" -le "$total_pages" ]; do
        response=$(curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
            "https://data-center.yunbisai.com/api/lswl-events?page=$page&keywords=&eventStatus=15&eventType=2&nameNumberType=63&month=1&areaNum=%E5%B9%BF%E4%B8%9C%E7%9C%81&order=&sort=&PageSize=36" 2>/dev/null)
        
        # 检查是否成功
        if echo "$response" | grep -q '"error":0'; then
            # 保存当前页数据
            echo "$response" > "$DATA_DIR/page_$page.json"
            
            # 提取数据并合并
            page_data=$(echo "$response" | grep -o '"rows":\[.*\]' | sed 's/"rows"://' | head -1)
            
            # 更新总页数
            total_pages=$(echo "$response" | grep -o '"TotalPage":[0-9]*' | grep -o '[0-9]*' | head -1)
            total_pages=${total_pages:-1}
            
            echo "Fetched page $page of $total_pages"
        else
            echo "Failed to fetch page $page"
            break
        fi
        
        page=$((page + 1))
        
        # 防止无限循环
        if [ "$page" -gt 10 ]; then
            break
        fi
    done
    
    # 合并所有页面数据
    cat "$DATA_DIR/page_"*.json 2>/dev/null | jq -s '[.[].datArr.rows[]]' > "$output_file" 2>/dev/null || echo "[]" > "$output_file"
    
    # 清理临时文件
    rm -f "$DATA_DIR/page_"*.json
    rm -f "$temp_file"
}

# 提取 event_id 列表
extract_event_ids() {
    local file=$1
    if [ -f "$file" ]; then
        cat "$file" | jq -r '.[].event_id' 2>/dev/null | sort -u
    fi
}

# 发送邮件函数
send_monitor_email() {
    local subject="$1"
    local body="$2"
    
    if [ -f "$EMAIL_SCRIPT" ]; then
        python3 "$EMAIL_SCRIPT" --to "$TO_EMAIL" --subject "$subject" --body "$body" 2>&1
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Email sent to $TO_EMAIL" >> "$LOG_FILE"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Email script not found: $EMAIL_SCRIPT" >> "$LOG_FILE"
    fi
}

# 主逻辑
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting monitor..." >> "$LOG_FILE"

# 步骤1: 创建目录
STEP_START=$(start_timer)
mkdir -p "$DATA_DIR"
end_timer "创建目录" "$STEP_START"

# 步骤2: 获取今天的数据
STEP_START=$(start_timer)
fetch_all_events "$TODAY_FILE"
end_timer "获取赛事数据" "$STEP_START"

# 步骤3: 提取 event_id 进行对比
STEP_START=$(start_timer)
today_ids=$(extract_event_ids "$TODAY_FILE")
total_count=$(echo "$today_ids" | wc -l)
end_timer "提取并对比赛事ID" "$STEP_START"

# 检查昨天的数据是否存在
if [ -f "$YESTERDAY_FILE" ]; then
    yesterday_ids=$(extract_event_ids "$YESTERDAY_FILE")
    
    # 找出新增的比赛
    new_events=$(comm -23 <(echo "$today_ids") <(echo "$yesterday_ids"))
    new_count=$(echo "$new_events" | grep -c '^[0-9]' 2>/dev/null || echo 0)
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Found $new_count new events" >> "$LOG_FILE"
    
    # 构建邮件内容
    email_subject="云比赛网围棋赛事监控报告 - $(date +%Y-%m-%d)"
    
    if [ "$new_count" -gt 0 ]; then
        echo "发现 $new_count 场新增围棋比赛！"
        
        # 获取新增比赛详情
        new_events_details=$(cat "$TODAY_FILE" | jq -r ".[] | select(.event_id as \$id | [\"$new_events\"] | index(\$id) | not) | empty")
        
        email_body=$(python3 << EOF
import json

events = json.load(open('$TODAY_FILE'))
new_ids = """$new_events""".strip().split('\n') if """$new_events""".strip() else []
new_ids = [int(x) for x in new_ids if x.strip()]

body = """云比赛网围棋赛事监控报告

监控日期: $(date +%Y-%m-%d)
对比日期: $(date -d yesterday +%Y-%m-%d) → $(date +%Y-%m-%d)

==============================
监控结果
==============================

发现 $new_count 场新增围棋比赛！

"""

# 新增比赛
for e in events:
    if e['event_id'] in new_ids:
        body += f"""
【{e['title']}】
  地点: {e['city_name']}{e['county_name']} | 主办方: {e['cname']}
  时间: {e.get('r_min_time', '').split('T')[0]} 至 {e.get('r_max_time', '').split('T')[0]}
  参赛: {e.get('play_num', '待定')} | 联系: {e.get('linkMan', '')} {e.get('contact', '')}
---
"""

body += f"""
==============================
广东省当前所有赛事列表（共 $total_count 场）
==============================

"""

# 按城市分组
from collections import defaultdict
cities = defaultdict(list)
for e in events:
    cities[e['city_name']].append(e)

for city in sorted(cities.keys()):
    body += f"\n=== {city} ===\n"
    for e in cities[city]:
        body += f"""
【{e['title']}】
  地点: {e['county_name']} | {e['cname']}
  时间: {e.get('r_min_time', '').split('T')[0]} 至 {e.get('r_max_time', '').split('T')[0]}
  参赛: {e.get('play_num', '待定')} | 联系: {e.get('linkMan', '')} {e.get('contact', '')}
---
"""

body += f"""
==============================
统计信息
==============================
新增比赛: $new_count 场
当前总数: $total_count 场

下次监控时间: 明天 07:00

---
本邮件由 OpenClaw 自动发送
"""

print(body)
EOF
)
    else
        echo "今日无新增比赛"
        
        email_body=$(python3 << EOF
import json

events = json.load(open('$TODAY_FILE'))

body = """云比赛网围棋赛事监控报告

监控日期: $(date +%Y-%m-%d)
对比日期: $(date -d yesterday +%Y-%m-%d) → $(date +%Y-%m-%d)

==============================
监控结果
==============================

今日无新增比赛

==============================
广东省当前所有赛事列表（共 $total_count 场）
==============================

"""

# 按城市分组
from collections import defaultdict
cities = defaultdict(list)
for e in events:
    cities[e['city_name']].append(e)

for city in sorted(cities.keys()):
    body += f"\n=== {city} ===\n"
    for e in cities[city]:
        body += f"""
【{e['title']}】
  地点: {e['county_name']} | {e['cname']}
  时间: {e.get('r_min_time', '').split('T')[0]} 至 {e.get('r_max_time', '').split('T')[0]}
  参赛: {e.get('play_num', '待定')} | 联系: {e.get('linkMan', '')} {e.get('contact', '')}
---
"""

body += f"""
==============================
统计信息
==============================
新增比赛: 0 场
当前总数: $total_count 场

下次监控时间: 明天 07:00

---
本邮件由 OpenClaw 自动发送
"""

print(body)
EOF
)
    fi
    
    # 步骤4: 生成性能报告并发送邮件
    STEP_START=$(start_timer)
    PERF_REPORT=$(format_perf_report)
    echo "$PERF_REPORT"
    email_body="${email_body}${PERF_REPORT}"
    send_monitor_email "$email_subject" "$email_body"
    end_timer "生成报告并发送邮件" "$STEP_START"

else
    # 首次运行
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] First run, saved $total_count events" >> "$LOG_FILE"
    echo "首次运行，已记录 $total_count 场比赛作为基准数据"
    
    email_subject="云比赛网围棋赛事监控 - 首次运行 - $(date +%Y-%m-%d)"
    
    email_body=$(python3 << EOF
import json

events = json.load(open('$TODAY_FILE'))

body = """云比赛网围棋赛事监控报告

监控日期: $(date +%Y-%m-%d)

==============================
首次运行
==============================

已记录 $total_count 场比赛作为基准数据

==============================
广东省当前所有赛事列表（共 $total_count 场）
==============================

"""

# 按城市分组
from collections import defaultdict
cities = defaultdict(list)
for e in events:
    cities[e['city_name']].append(e)

for city in sorted(cities.keys()):
    body += f"\n=== {city} ===\n"
    for e in cities[city]:
        body += f"""
【{e['title']}】
  地点: {e['county_name']} | {e['cname']}
  时间: {e.get('r_min_time', '').split('T')[0]} 至 {e.get('r_max_time', '').split('T')[0]}
  参赛: {e.get('play_num', '待定')} | 联系: {e.get('linkMan', '')} {e.get('contact', '')}
---
"""

body += """
从明天开始将检测新增比赛。

下次监控时间: 明天 07:00

---
本邮件由 OpenClaw 自动发送
"""

print(body)
EOF
)
    
    # 步骤4: 生成性能报告并发送邮件
    STEP_START=$(start_timer)
    PERF_REPORT=$(format_perf_report)
    echo "$PERF_REPORT"
    email_body="${email_body}${PERF_REPORT}"
    send_monitor_email "$email_subject" "$email_body"
    end_timer "生成报告并发送邮件" "$STEP_START"
fi

# 步骤5: 清理旧数据（保留最近30天）
STEP_START=$(start_timer)
find "$DATA_DIR" -name "events_*.json" -mtime +30 -delete 2>/dev/null
end_timer "清理旧数据" "$STEP_START"

# 输出最终性能报告
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Monitor completed" >> "$LOG_FILE"
echo ""
echo "✅ 云比赛网监控完成"
format_perf_report
