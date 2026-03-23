use anyhow::Result;
use bincode;
use blake3;
use clap::Parser;
use hex;
use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process;

/// #lazy-build
/// 检测源文件是否需要编译，并在需要时调用给定的命令
#[derive(Parser, Debug)]
#[command(author,version,about,long_about=None)]
struct Args {
    ///源码路径
    src: PathBuf,

    ///生成的二进制路径
    bin: PathBuf,

    ///构建命令
    #[arg(last = true)]
    cmd: Vec<String>,
}

fn get_file_hash<T: AsRef<Path>>(path: &T) -> Result<blake3::Hash> {
    let mut f = File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut buf = [0; 0x10000];

    loop {
        let l = f.read(&mut buf)?;
        if l == 0 {
            break;
        }
        hasher.update(&buf[..l]);
    }
    Ok(hasher.finalize())
}

fn get_db_file_name<P: AsRef<Path>>(src_file_path: &P, cmd: &Vec<String>) -> Result<PathBuf> {
    let src_file_hash = get_file_hash(src_file_path)?;

    let data = (src_file_hash.as_bytes(), cmd);
    let data = bincode::serialize(&data).unwrap();

    let hash = blake3::hash(&data);
    let s = hash.to_hex().to_string();
    let p = PathBuf::from(s);
    Ok(p)
}

fn run_build_cmd(cmd: &Vec<String>) -> Result<i32> {
    let (program, args) = cmd.split_first().unwrap();
    let res = process::Command::new(program).args(args).status()?;
    Ok(res.code().unwrap())
}

fn check(bin_file_path: &Path, db_file_path: &Path) -> bool {
    let Ok(old_hash) = fs::read(db_file_path) else {
        return false;
    };
    println!("找到记录 {:?}", db_file_path);
    println!("\t{}", hex::encode(&old_hash));

    let Ok(bin_hash) = get_file_hash(&bin_file_path) else {
        return false;
    };
    let bin_hash = bin_hash.as_bytes();
    println!("找到 {:?}", bin_file_path);
    println!("\t{}", hex::encode(bin_hash));

    old_hash == bin_hash
}

fn main() {
    let db_dir = std::env::temp_dir().join("lazy-build-db");

    fs::create_dir_all(&db_dir).expect(format!("{:?} 创建失败", db_dir).as_str());

    let args = Args::parse();
    if !args.src.exists() {
        eprint!("{:?} 不存在", &(args.src));
        process::exit(1);
    }

    println!("src: {:?}", args.src);
    println!("bin: {:?}", args.bin);
    println!("cmd: {:?}", args.cmd);

    let db_file_name = get_db_file_name(&args.src, &args.cmd).unwrap();
    let db_file_path = db_dir.join(db_file_name);

    if check(&args.bin, &db_file_path) {
        println!("构建已跳过");
        process::exit(0);
    }

    println!("使用命令 {:?} 构建", args.cmd);

    let Ok(code) = run_build_cmd(&args.cmd) else {
        println!("构建失败 ");
        process::exit(1);
    };
    if code != 0 {
        println!("构建失败 exit code:{}", code);
        process::exit(code);
    }
    println!("构建成功 exit code:{}", code);
    let Ok(new_bin_hash) = get_file_hash(&args.bin) else {
        println!("未找到构建结果 {:?}", &args.bin);
        process::exit(1);
    };
    println!("找到构建结果 {:?}", &args.bin);
    println!("\t{}", hex::encode(new_bin_hash.as_bytes()));
    match fs::write(&db_file_path, new_bin_hash.as_bytes()) {
        Ok(_) => {
            println!("写入条目 {:?}", db_file_path);
            process::exit(0)
        }
        Err(_) => {
            println!("写入条目 {:?} 失败", db_file_path);
            process::exit(1)
        }
    };
}
