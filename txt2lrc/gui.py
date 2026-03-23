#!/usr/bin/env python3
"""
txt2lrc GUI - 跨平台图形界面版本
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import txt2lrc

class Txt2LrcGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("txt2lrc - TXT到LRC转换器")
        self.setGeometry(100, 100, 600, 400)
        self.setup_ui()

    def setup_ui(self):
        # 主界面控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        # 输入部分
        form_layout = QFormLayout()

        # 输入文件/目录
        input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("选择输入文件或目录")
        input_browse_btn = QPushButton("浏览...")
        input_browse_btn.clicked.connect(lambda: self.browse_path(self.input_line, "选择输入文件"))
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(input_browse_btn)
        form_layout.addRow("输入:", input_layout)

        # 输出目录
        output_layout = QHBoxLayout()
        self.output_line = QLineEdit()
        self.output_line.setPlaceholderText("选择输出目录")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(lambda: self.browse_path(self.output_line, "选择输出目录", True))
        output_layout.addWidget(self.output_line)
        output_layout.addWidget(output_browse_btn)
        form_layout.addRow("输出目录:", output_layout)

        # 选项
        self.title_checkbox = QCheckBox("添加标题到LRC")
        form_layout.addRow("", self.title_checkbox)

        layout.addLayout(form_layout)

        # 处理按钮
        self.process_btn = QPushButton("开始转换")
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setFixedHeight(35)
        layout.addWidget(self.process_btn)

        # 日志显示
        layout.addWidget(QLabel("处理日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)

        central_widget.setLayout(layout)

        # 现代化风格
        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QMainWindow {
                background-color: #f8f9fa;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 5px;
                background-color: #0078d7;
                color: white;
                border: none;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #107c10;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0078d7;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox {
                spacing: 8px;
            }
            QLabel {
                font-weight: 500;
            }
        """)

    def browse_path(self, line_edit, title, is_dir=False):
        if is_dir:
            path = QFileDialog.getExistingDirectory(self, title)
        else:
            path, _ = QFileDialog.getOpenFileName(self, title, "", "Text Files (*.txt);;All Files (*)")
            if not path:
                path = QFileDialog.getExistingDirectory(self, "选择输入目录")
        if path:
            line_edit.setText(path)

    def process_files(self):
        input_path_str = self.input_line.text().strip()
        output_path_str = self.output_line.text().strip()
        if not input_path_str:
            QMessageBox.warning(self, "错误", "请选择输入文件或目录")
            return
        if not output_path_str:
            QMessageBox.warning(self, "错误", "请选择输出目录")
            return

        input_path = Path(input_path_str)
        output_dir = Path(output_path_str)
        add_title = self.title_checkbox.isChecked()

        if not input_path.exists():
            QMessageBox.warning(self, "错误", "输入路径不存在")
            return

        self.log_text.clear()
        self.log_text.append("开始处理...\n")

        try:
            cnt = 0
            if input_path.is_file():
                if input_path.suffix.lower() != '.txt':
                    QMessageBox.warning(self, "错误", "输入文件必须是txt格式")
                    return
                self.process_single_file(input_path, output_dir / input_path.stem, add_title)
                cnt = 1
            elif input_path.is_dir():
                output_sub_dir = output_dir / input_path.name
                output_sub_dir.mkdir(parents=True, exist_ok=True)
                for f in input_path.rglob("*.txt"):
                    # 计算相对路径，保持目录结构
                    relative_path = f.relative_to(input_path).with_suffix('')
                    out_base = output_sub_dir / relative_path
                    self.process_single_file(f, out_base, add_title)
                    cnt += 1
            else:
                QMessageBox.warning(self, "错误", "输入路径无效")
                return

            self.log_text.append(f"\n处理完成，共转换了 {cnt} 个文件")

        except Exception as e:
            self.log_text.append(f"\n发生错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"处理过程中发生错误:\n{str(e)}")

    def process_single_file(self, file_path, out_base, add_title):
        try:
            str_list = file_path.read_text(encoding="utf-8").splitlines()
            if add_title:
                str_list.insert(0, file_path.name)
                str_list.insert(1, "-" * 40)
            txt2lrc.gen(out_base, str_list)
            self.log_text.append(f"已转换: {file_path} -> {out_base.with_suffix('.lrc')}")
        except Exception as e:
            self.log_text.append(f"转换失败 {file_path}: {str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 现代化外观
    window = Txt2LrcGUI()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
