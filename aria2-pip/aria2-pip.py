"""
@author: xu-haozhe
@date: 2025/07/28

aria2-pip
用 aria2 加速 pip 下载!!
环境：
    ubuntu 24.04
    python 3.12.3
    pip 24.0|25.1.1
    requests 2.32.4
"""

import requests
import os
import logging
import time
import importlib
import sys
from typing import Dict, Any, TYPE_CHECKING, Iterable, Tuple


# --- 配置区 ---
PATCH_COMMANDS=['install']
ARIA2_RPC_URL = os.environ.get("ARIA2_RPC_URL", "http://localhost:6800/jsonrpc")
ARIA2_RPC_SECRET = os.environ.get("ARIA2_RPC_SECRET", "")
# --- 配置区结束 ---

logging.basicConfig(level=logging.INFO, format='[aria2-pip %(levelname)s] %(message)s')
logger=logging.getLogger()

if sys.stdout.isatty():
    COLOR_GREEN = '\033[92m'
    COLOR_RED = '\033[91m'
    COLOR_BLUE = '\033[94m'
    COLOR_DIM = '\033[2m'
    COLOR_RESET = '\033[0m'
    def _format_size(size_in_bytes: float) -> str:
        if size_in_bytes < 1024:  return f"{int(size_in_bytes)} B"
        if size_in_bytes < 1024**2:  return f"{size_in_bytes/1024:.1f} KB"
        if size_in_bytes < 1024**3:  return f"{size_in_bytes/(1024**2):.1f} MB"
        return f"{size_in_bytes/(1024**3):.1f} GB"
    def _format_eta(seconds: float|None) -> str:
        if seconds is None:  return "--:--:--"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
    def _progress_bar(status)->str:
        total_length = int(status.get("totalLength", 0))
        completed_length = int(status.get("completedLength", 0))
        download_speed = int(status.get("downloadSpeed", 0))
        eta_seconds = (total_length - completed_length) / download_speed if download_speed > 0 else None
        bar_width=40
        filled_len=int(40*completed_length/total_length) if total_length > 0 else 40
        bar=(f"{COLOR_GREEN}{'━' * filled_len}{COLOR_RESET}"
             f"{COLOR_DIM}{'━' * (bar_width - filled_len)}{COLOR_RESET}")
        size_str = f"{COLOR_GREEN}{_format_size(completed_length)}/{_format_size(total_length)}{COLOR_RESET}"
        speed_str = f"{COLOR_RED}{_format_size(download_speed)}/s{COLOR_RESET}"
        eta_str = f"{COLOR_BLUE}{_format_eta(eta_seconds)}{COLOR_RESET}"
        return f"  {bar} {size_str.rjust(18)} {speed_str.rjust(12)} eta {eta_str}"

    def _show_progress_bar(meta_info:Iterable[Tuple[str,str,str]],status:Iterable[Dict])->None:
        if len(meta_info)==0:return
        if len(meta_info)!=len(status):
            raise ValueError("meta_info and status must have the same length")
        sys.stdout.write(f"\033[{len(meta_info)*2}A")
        for (name,_,_),status in zip(meta_info,status):
            sys.stdout.write(name+"\033[K\n")
            sys.stdout.write(_progress_bar(status[0])+"\033[K\n")
        pass
else:
    COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_DIM, COLOR_RESET = "", "", "", "", ""
    def _show_progress_bar(meta_info:Iterable[Tuple[str,str,str]],status:Iterable[Dict])->None:
        pass

def _aria2_rpc_call(method: str, params: list) -> Dict[str, Any]:
    if ARIA2_RPC_SECRET:
        params.insert(0, f"token:{ARIA2_RPC_SECRET}")
    payload = {
        "jsonrpc": "2.0",
        "id": f"fastpip-{method}",
        "method": method,
        "params": params,
    }
    response = requests.post(ARIA2_RPC_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()
def _aria2_rpc_multicall(method:str,params:list[list])->list[Any]:
    payload = {
        "jsonrpc": "2.0",
        "id": f"fastpip-multicall-{method}",
        "method": "system.multicall",
        "params": [[
            {
                "methodName": method,
                "params": [f"token:{ARIA2_RPC_SECRET}"]+param if ARIA2_RPC_SECRET else param,
            }for param in params
        ]],
    }
    response = requests.post(ARIA2_RPC_URL, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()['result']

def _check_aria2c_connection():
    logger.info(f"正在检查 aria2c RPC 服务于 {ARIA2_RPC_URL}...")
    try:
        result=_aria2_rpc_call("aria2.getVersion", [])
        if "error" in result:
            logger.error(f"连接 aria2c RPC 失败: {result['error']['message']}")
            return False
        version = result.get("result", {}).get("version", "未知")
        logger.info(f"成功连接到 aria2c (版本: {version})。")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"无法连接到 aria2c RPC 服务: {e}")
        logger.error("请确保 aria2c 正在后台以 RPC 模式运行。")
        return False
    
def _get_http_response_filename(resp, link):
    return link.filename

def _wait_aria2(meta_infos:Iterable[Tuple[str,str,str]],gids:Iterable[str]):
    for name,_,_ in meta_infos:
        sys.stdout.write(name+"\033[K\n\033[k\n")
    while True:
        try:
            result=_aria2_rpc_multicall("aria2.tellStatus",[
                [gid] for gid in gids
            ])
            for status in result:
                if 'code' in status[0]:
                    raise RuntimeError(f"aria2 报告错误: {status[0]['message']}")
            _show_progress_bar(meta_infos,result)
            if all(status[0].get("status")=="complete" for status in result):
                break
        except requests.exceptions.RequestException as e:
            logger.error(f"轮询 aria2 状态时出错: {e}")
            raise
        time.sleep(1)
    logger.info("下载完成")

        

class Aria2Downloader:
    from pip._internal.models.link import Link
    def __init__(self,session,progress_bar: str,resume_retries: int|None=None):
        self._session = session
        self._progress_bar = progress_bar
    def __call__(self, links:Iterable|Link, location)->Iterable[Tuple[Link, Tuple[str, str]]]|tuple[str,str]:
        is_batch = not isinstance(links,self.Link)
        if not is_batch:  links=[links]
        meta_info=[self._get_meta_info(link) for link in links]
        try:
            result=_aria2_rpc_multicall("aria2.addUri",[
                [[final_url], {"dir": location, "out": filename}]
                for filename, content_type, final_url in meta_info
            ])
            for gid in result:
                if 'code' in gid[0]:
                    raise RuntimeError(f"aria2 添加任务失败: {gid[0]['message']}")
            gids=[gid[0] for gid in result]
        except requests.exceptions.RequestException|RuntimeError as e:
            logger.error(f"无法将下载任务添加到 aria2: {e}")
            raise
        _wait_aria2(meta_info,gids)
        _aria2_rpc_multicall("aria2.removeDownloadResult", [
            [gid] for gid in gids
        ])
        if is_batch:
            return [
                (link,(os.path.join(location,filename),content_type))
                for link,(filename, content_type, url) in zip(links,meta_info)
            ]
        else:
            filename,content_type,url=meta_info[0]
            return (os.path.join(location,filename),content_type)
    def _get_meta_info(self,link)->tuple[str,str,str]:
        """
        return : name,content_type,url
        """
        logger.info(f"正在为 {link.filename} 获取下载元信息...")
        try:
            head_response = self._session.head(link.url, allow_redirects=True, stream=True)
            head_response.raise_for_status()
            return (
                _get_http_response_filename(head_response, link),
                head_response.headers.get("Content-Type", ""),
                head_response.url
            )
        except Exception as e:
            logger.error(f"获取元信息失败: {e}")
            raise e
        
def patch_downloader()->bool:
    if not _check_aria2c_connection():
        logger.warning("aria2c 服务不可用，将回退到 pip 默认下载器。")
        return False
    try:
        from pip._internal.operations import prepare as pip_prepare
        from pip._internal.network.download import _get_http_response_filename as pip_get_http_response_filename
    except ImportError as e:
        logger.error(f"无法从 pip 导入必要模块: {e}。脚本可能与 pip 版本不兼容。")
        raise
        return False
    global _get_http_response_filename
    _get_http_response_filename=pip_get_http_response_filename
    pip_prepare.BatchDownloader=Aria2Downloader
    pip_prepare.Downloader=Aria2Downloader
    logger.info("Patch 成功！下载将由 aria2c 处理。")

def patch_create_command()->bool:
    try:
        from pip._internal import commands as pip_commands
    except ImportError as e:
        logger.error(f"无法从 pip 导入必要模块: {e}。脚本可能与 pip 版本不兼容。")
        raise
    old_create_commands=pip_commands.create_command
    def patched_create_commands(name: str, **kwargs: Any):
        command=old_create_commands(name,**kwargs)
        if name.strip() in PATCH_COMMANDS:
            logger.info(f"检测到命令 {name}，尝试进行 Patch...")
            patch_downloader()
        return command
    pip_commands.create_command=patched_create_commands
    return True


def main()->None:
    patch_create_command()
    try:
        from pip._internal.cli.main import main as pip_main
        sys.exit(pip_main())
    except Exception as e:
        logger.error(f"pip 运行时出现未知错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

