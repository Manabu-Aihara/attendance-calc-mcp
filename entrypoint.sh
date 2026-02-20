#!/bin/sh

# 環境変数を.envファイルから読み込む
# ローカルの場合、ここ使う
set -a
. /.env
set +a

# SSHの設定ディレクトリをクリーンアップ
rm -rf /root/.ssh
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# SSHトンネルの設定をバックグラウンドで実行
sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -N -L 3307:127.0.0.1:3306 -p 9001 "$SAKURA_USER"@"$SAKURA_ADDRESS" &
SSH_PID=$!

# SSHトンネルの確立を少し待つ
sleep 5

# Gunicornを起動
# ローカルの場合、8001ポートでアプリケーションを起動
exec poetry run uvicorn app.server.endpoint:app --host 0.0.0.0 --port 8001 --reload