#!/bin/zsh
# 每日 X 帖提醒:挑当天最该发的比赛,出卡图+写文案,飞书推给用户手动发。本地 cron 调用。
cd /Users/yishuai/develop/ai/make-money/projects/worldcup2026 || exit 1
set -a; source /Users/yishuai/develop/ai/make-money/.env; set +a
echo "=== $(date) ===" >> /tmp/oraclexi_x.log
/Users/yishuai/anaconda3/bin/python3 x_daily.py >> /tmp/oraclexi_x.log 2>&1
