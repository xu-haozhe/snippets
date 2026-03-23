# lazy-build

通过哈希判断文件是否需要编译，在打线上赛的时候能节省些时间。

使用 blake3 哈希。

会检查原始文件、编译命令、目标文件的哈希。

坏消息同样是我只在 linux 上用过。

## 命令行参数

```sh
#lazy-build 检测源文件是否需要编译，并在需要时调用给定的命令

Usage: lazy-build <SRC> <BIN> [-- <CMD>...]

Arguments:
  <SRC>     源码路径
  <BIN>     生成的二进制路径
  [CMD]...  构建命令

Options:
  -h, --help     Print help
  -V, --version  Print version
```

## 怎么配置

搞到 tasks.json 里面，包装原有的编译命令

例如，原来的：

```json
{
    "type": "cppbuild",
    "label": "C/C++: g++ 生成活动文件",
    "command": "/usr/bin/g++",
    "args": [
        "-fdiagnostics-color=always",
        "-g",
        "${file}",
        "-o",
        "${fileDirname}/${fileBasenameNoExtension}"
    ],
    "options": {
        "cwd": "${fileDirname}"
    },
    "problemMatcher": [
        "$gcc"
    ],
    "group": {
        "kind": "build",
        "isDefault": true
    },
}
```

改成:

```json
{
    "type": "cppbuild",
    "label": "C/C++: g++ 生成活动文件",
    "command": "lazy-build",
    "args": [
        "${file}",
        "${fileDirname}/${fileBasenameNoExtension}",
        "--",
        "/usr/bin/g++",
        "-fdiagnostics-color=always",
        "-g",
        "${file}",
        "-o",
        "${fileDirname}/${fileBasenameNoExtension}"
    ],
    "options": {
        "cwd": "${fileDirname}"
    },
    "problemMatcher": [
        "$gcc"
    ],
    "group": {
        "kind": "build",
        "isDefault": true
    },
}
```

## 清空数据

数据存在`/tmp/lazy-build-db` 里面，正常情况下只要重启就清空了。或者你也可以直接给它们删了。