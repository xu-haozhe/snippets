use clap::Parser;
use log;
use pathdiff;
use serde::{Deserialize, Serialize};
use simple_logger;
use std::cmp::Ordering;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;
use std::time::{SystemTime, UNIX_EPOCH};
use toml;
use toml::Value;

#[derive(Parser, Debug)]
#[command(author,version,about,long_about=None)]
struct Args {
    ///工作目录
    dir: PathBuf,

    ///Cargo.toml
    toml: PathBuf,

    ///rs file，若有则尝试添加
    rs: Option<PathBuf>,

    ///最大 bin 项数，不提供则不限制数量
    #[arg(short, long)]
    max_len: Option<usize>,
}

fn default_time() -> SystemTime {
    UNIX_EPOCH
}

#[allow(dead_code)]
#[derive(Serialize, Deserialize, Debug, Default)]
struct UnChecked;
#[derive(Serialize, Deserialize, Debug, Default)]
#[allow(dead_code)]
struct Checked;

// impl UnChecked {
//     fn default() -> Self {Self{}}
// }
// impl Checked {
//     fn default() -> Self {Self{}}
// }

#[derive(Serialize, Deserialize, Debug)]
struct BinItem<S> {
    name: String,
    path: PathBuf,

    #[serde(skip, default = "default_time")]
    time: SystemTime,

    #[serde(skip)]
    _state: std::marker::PhantomData<S>,
}
impl BinItem<UnChecked> {
    pub fn check(self, dir: &Path) -> Option<BinItem<Checked>> {
        let Ok(m) = fs::metadata(dir.join(&self.path)) else {
            return None;
        };
        let Ok(t) = m.modified() else {
            return None;
        };

        Some(BinItem {
            name: self.name,
            path: self.path,
            time: t,
            _state: std::marker::PhantomData::<Checked>,
        })
    }
}

impl Ord for BinItem<Checked> {
    fn cmp(&self, other: &Self) -> Ordering {
        other.time.cmp(&self.time)
    }
}
impl PartialEq for BinItem<Checked> {
    fn eq(&self, other: &Self) -> bool {
        self.time == other.time
    }
}
impl Eq for BinItem<Checked> {}
impl PartialOrd for BinItem<Checked> {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Serialize, Deserialize, Debug)]
struct CargoToml<S> {
    #[serde(default)]
    bin: Vec<BinItem<S>>,

    #[serde(flatten)]
    extra: HashMap<String, Value>,

    #[serde(skip)]
    _state: std::marker::PhantomData<S>,
}

impl CargoToml<UnChecked> {
    pub fn check(self, dir: &Path) -> CargoToml<Checked> {
        let checked_bins = self
            .bin
            .into_iter()
            .filter_map(|item| item.check(dir))
            .collect();
        CargoToml {
            bin: checked_bins,
            extra: self.extra,
            _state: std::marker::PhantomData,
        }
    }
}
impl CargoToml<Checked> {
    pub fn process_bins(&mut self, max_len: usize) {
        self.bin.sort();
        self.bin.truncate(max_len);
    }
}

fn main() {
    let args = Args::parse();
    simple_logger::init_with_level(log::Level::Info).unwrap();
    if !args.dir.exists() {
        log::error!("{:?} 不存在", args.dir);
        process::exit(1);
    }
    if !args.toml.starts_with(&args.dir) {
        log::warn!("{:?} 不在工作目录 {:?} 中", args.toml, args.dir)
    }

    let cargo_toml = match fs::read_to_string(&args.toml) {
        Ok(s) => s,
        Err(_) => {
            log::warn!("{:?} 不存在，使用默认设置", args.toml);
            r#"
            [package]
            name = "no-name"
            version = "0.1.0"
            edition = "2024"

            [dependencies]
            "#
            .to_string()
        }
    };

    let Ok(cargo_toml) = toml::from_str::<CargoToml<UnChecked>>(&cargo_toml) else {
        log::error!("{:?} 解析失败", args.toml);
        process::exit(0);
    };

    let mut cargo_toml = cargo_toml.check(&args.dir);

    if let Some(p) = args.rs {
        if !p.starts_with(&args.dir) {
            log::warn!("{:?} 不在工作目录 {:?} 中", p, args.dir)
        }
        let Some(p) = pathdiff::diff_paths(&p, &args.dir) else {
            log::error!("无法处理路径 {:?}", &p);
            process::exit(1);
        };
        if !cargo_toml.bin.iter().any(|b| b.path == p) {
            let b = BinItem {
                name: p.to_string_lossy().into_owned(),
                path: p.clone(),
                time: UNIX_EPOCH,
                _state: std::marker::PhantomData::<UnChecked>,
            };
            let Some(b) = b.check(&args.dir) else {
                log::error!("{:?} 不存在", p);
                process::exit(1);
            };
            cargo_toml.bin.push(b);
        }
    };
    if let Some(len) = args.max_len {
        cargo_toml.process_bins(len);
    };
    let cargo_toml = toml::to_string(&cargo_toml).unwrap();

    let Ok(_) = fs::write(&args.toml, cargo_toml) else {
        log::error!("无法写入 {:?}", args.toml);
        process::exit(1);
    };
    log::info!("成功写入 {:?}", args.toml);
    process::exit(0);
}
