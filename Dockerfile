# 二开推荐阅读[如何提高项目构建效率](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/scene/build/speed.html)
# 选择基础镜像。如需更换，请到[dockerhub官方仓库](https://hub.docker.com/_/python?tab=tags)自行选择后替换。
# 已知alpine镜像与pytorch有兼容性问题会导致构建失败，如需使用pytorch请务必按需更换基础镜像。
FROM docker.m.daocloud.io/library/python:3.10-slim

# 1) 证书 + 基础工具（Debian系用 apt-get，不是 apk）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# 2) 容器默认时区为UTC，如需使用上海时间可启用（可选）
# ENV TZ=Asia/Shanghai

# 3) 拷贝当前项目到/app目录下（.dockerignore中文件除外）
COPY . /app

# 4) 设定当前的工作目录
WORKDIR /app

# 5) 安装依赖
# 选用国内镜像源以提高下载速度
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
    && pip config set global.trusted-host mirrors.cloud.tencent.com \
    && pip install --upgrade pip \
    && pip install -r requirements.txt

# 6) 暴露端口（需与云托管设置一致）
EXPOSE 80

# 7) 启动命令
CMD ["python3", "run.py", "0.0.0.0", "80"]
