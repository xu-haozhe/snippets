from pathlib import Path
import argparse

null_wav = bytearray([
    # RIFF头
    0x52, 0x49, 0x46, 0x46,  # "RIFF"
    0x25, 0x00, 0x00, 0x00,  # 文件大小-8 (37)
    0x57, 0x41, 0x56, 0x45,  # "WAVE"
    # fmt块
    0x66, 0x6d, 0x74, 0x20,  # "fmt "
    0x10, 0x00, 0x00, 0x00,  # fmt块大小 (16)
    0x01, 0x00,              # PCM格式
    0x01, 0x00,              # 单声道
    0x01, 0x00, 0x00, 0x00,  # 1 Hz
    0x01, 0x00, 0x00, 0x00,  # 1 字节/秒
    0x01, 0x00,              # 块对齐 (1字节)
    0x08, 0x00,              # 8位深度
    # data块
    0x64, 0x61, 0x74, 0x61,  # "data"
    0x01, 0x00, 0x00, 0x00,  # 数据大小 (1字节)
    0x80                      # 静音采样 (128)
])

def time_str(t:int):
    """"""
    t=int(t)
    return f"[{t//6000}:{((t//100)%60):02}.{t%100:02}]"

def lrc(text:list[str])->bytes:
    return "\n".join([time_str(i)+t for i,t in enumerate(text)]).encode("utf-8")

def wav()->bytes:
    return null_wav

def gen(dir:Path,text:list[str])->None:
    (dir.with_suffix(".wav")).write_bytes(null_wav)
    (dir.with_suffix(".lrc")).write_bytes(lrc(text))


def main()->None:

    argparser = argparse.ArgumentParser(description="txt2lrc 将txt文件转成供辞典笔等播放器使用的lrc与wav")
    argparser.add_argument("-i", "--input", type=Path, required=True, help="input file or dir")
    argparser.add_argument("-o", "--output", type=Path, default=None, help="output file or dir")
    argparser.add_argument("--title", action="store_true", help="add title to lrc")
    args = argparser.parse_args()

    in_path:Path=args.input
    out_path:Path=args.output
    add_title:bool=args.title

    def proc_file(file:Path,out_path:Path)->None:
        str_list=file.read_text(encoding="utf-8").splitlines()
        if add_title:
            str_list.insert(0,f"{file.stem}")
            str_list.insert(1,"-"*40)
        gen(out_path,str_list)

    if in_path.is_file():
        out_path=out_path or in_path.stem
        proc_file(in_path,out_path)

    if in_path.is_dir():
        out_path=out_path or in_path.parent/(in_path.name+'_lrc')
        cnt=0
        for f in in_path.rglob("*.txt"):
            proc_file(f,out_path)
            cnt+=1
        print(f"共处理了{cnt}个文件")
        exit(0)

if __name__=="__main__":
    main()