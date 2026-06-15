#!/bin/zsh
# 本地定时任务:拉比分→生成战报(DeepSeek/MiniMax,用本地.env密钥)→推送触发CI部署。
# 密钥只在本地,绝不上 GitHub。日志 /tmp/oraclexi_blog.log。
cd /Users/yishuai/develop/ai/make-money/projects/worldcup2026 || exit 1
set -a; source /Users/yishuai/develop/ai/make-money/.env; set +a
PY=/Users/yishuai/anaconda3/bin/python3
LOG=/tmp/oraclexi_blog.log
echo "=== $(date) ===" >> $LOG
# git 同步失败必须中止,别在错乱状态上构建;数据脚本各自容错(一个挂了不连累其他,落盘是原子的)
git pull --rebase --autostash origin main >> $LOG 2>&1 || { echo "pull failed @ $(date), abort" >> $LOG; exit 1; }
$PY update_results.py      >> $LOG 2>&1 || echo "update_results failed @ $(date)" >> $LOG  # 最新比分
$PY refresh_predictions.py >> $LOG 2>&1 || echo "refresh_predictions failed @ $(date)" >> $LOG  # 赛前重算,开球冻结
$PY gen_blog.py            >> $LOG 2>&1 || echo "gen_blog failed @ $(date)" >> $LOG  # 新比赛写战报
# 只在有新战报或新比分时才推(忽略 meta.json 纯时间戳变化,避免空部署)
if [[ -n "$(git status --porcelain data/blog.json assets/blog data/groups.json)" ]]; then
  git add data/blog.json assets/blog data/groups.json data/meta.json
  if git commit -q -m "auto: 战报与比分更新" >> $LOG 2>&1 && git push origin HEAD:main >> $LOG 2>&1; then
    echo "pushed @ $(date)" >> $LOG
  else
    echo "commit/push failed @ $(date)" >> $LOG
  fi
else
  echo "no changes" >> $LOG
fi
