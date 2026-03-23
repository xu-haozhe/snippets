# gen-cargo-toml

自动把 `rs` 文件作为 `bin` 写到 `Cargo.toml` 里面，实现某种意义上的单文件 rust，如果你在用 rust 刷题会非常有用。

不过一个坏消息是，我只在 linux 上测试过它。

## 命令行参数

```sh
Usage: gen-cargo-toml [OPTIONS] <DIR> <TOML> [RS]

Arguments:
  <DIR>   工作目录
  <TOML>  Cargo.toml
  [RS]    rs file，若有则尝试添加

Options:
  -m, --max-len <MAX_LEN>  最大 bin 项数，不提供则不限制数量
  -h, --help               Print help
  -V, --version            Print version
```

## 具体怎么用？

通常我会在 vscode 中配合 [Run On Save 插件](https://marketplace.visualstudio.com/items?itemName=emeraldwalk.RunOnSave) 使用

settings.json:

```json
{    
    "emeraldwalk.runonsave": {
        "commands": [
            {
                "match": "\\.rs$",
                "cmd": "gen-cargo-toml ${workspaceFolder} ${workspaceFolder}/Cargo.toml ${file} --max-len 50"
            }
        ]
    }
}
```

推荐设置一个最大项数