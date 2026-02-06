# python3.12.3のイメージをダウンロード
FROM python:3.12.3-slim

WORKDIR /workdir

# ローカルの場合、8001
EXPOSE 8001

# pipを使ってpoetryをインストール
RUN pip install poetry

# poetryの定義ファイルをコピー (存在する場合)
COPY pyproject.toml* poetry.lock* poetry.toml* /workdir/
COPY app /workdir/app
# poetryでライブラリをインストール (pyproject.tomlが既にある場合)
# RUN poetry config virtualenvs.in-project true
RUN if [ -f pyproject.toml ]; then poetry install --no-root; fi

RUN apt-get update && apt-get install -y openssh-client sshpass

# uvicornのサーバーを立ち上げる
# ENTRYPOINT [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# ポートフォーワーディングの設定
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh
# ローカルの場合、ここ使う
COPY id_rsa /root/.ssh/id_rsa
COPY .env /.env

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 環境変数を設定
ENV SSH_PASSWORD=${SSH_PASSWORD}
ENV SAKURA_USER=${SAKURA_USER}
ENV SAKURA_ADDRESS=${SAKURA_ADDRESS}

ENTRYPOINT "/entrypoint.sh"