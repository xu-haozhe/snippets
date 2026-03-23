# aria2-pip

用 aria2 加速 pip 下载!!

用了 monkeypatch。

我只在linux上测试过，并且它依赖 pip 内部实现，新的 pip 估计已经用不了了。只是随便写写，~~建议直接配置镜像源~~

## 环境：

ubuntu 24.04

python 3.12.3

pip 24.0|25.1.1

requests 2.32.4

## 用法

需要本地有 aria2 服务，不习惯命令行的话 motrix 下载器也是不错的选择

在脚本开头配置好

```py
# --- 配置区 ---
PATCH_COMMANDS=['install']
ARIA2_RPC_URL = os.environ.get("ARIA2_RPC_URL", "http://localhost:6800/jsonrpc")
ARIA2_RPC_SECRET = os.environ.get("ARIA2_RPC_SECRET", "")
# --- 配置区结束 ---
```

然后像用 pip 一样用这个脚本