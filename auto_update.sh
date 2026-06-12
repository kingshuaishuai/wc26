#!/bin/zsh
# 本地定时任务:拉比分→生成战报(DeepSeek/MiniMax,用本地.env密钥)→推送触发CI部署。
# 密钥只在本地,绝不上 GitHub。日志 /tmp/oraclexi_blog.log。
#
# ⏸ 已停用(2026-06-13):站点暂不投入资源,停止 API 开销(博客/动态预测)。
#   站点静态部分仍在 Cloudflare 免费运行,比分靠免密钥的 GitHub CI 自动更新。
#   要恢复:删掉下面这行 exit 0 即可。
exit 0
cd /Users/yishuai/develop/ai/make-money/projects/worldcup2026 || exit 1
set -a; source /Users/yishuai/develop/ai/make-money/.env; set +a
PY=/Users/yishuai/anaconda3/bin/python3
LOG=/tmp/oraclexi_blog.log
echo "=== $(date) ===" >> $LOG
git pull --rebase --autostash origin main >> $LOG 2>&1
$PY update_results.py      >> $LOG 2>&1   # 最新比分(让博客识别新结束的比赛)
$PY refresh_predictions.py >> $LOG 2>&1   # 动态预测:赛前用最新球队新闻重算,开球冻结
$PY gen_blog.py            >> $LOG 2>&1   # 已生成的跳过,只为新比赛写战报
# 只在有新战报或新比分时才推(忽略 meta.json 纯时间戳变化,避免空部署)
if [[ -n "$(git status --porcelain data/blog.json assets/blog data/groups.json)" ]]; then
  git add data/blog.json assets/blog data/groups.json data/meta.json
  git commit -q -m "auto: 战报与比分更新" >> $LOG 2>&1
  git push origin HEAD:main >> $LOG 2>&1
  echo "pushed @ $(date)" >> $LOG
else
  echo "no changes" >> $LOG
fi
