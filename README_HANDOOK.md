# 《具身智能导论》实验手册（Material for MkDocs）

本目录在原 EAI_project 代码基础上新增了 MkDocs Material 文档，不改动原实验代码。

## 启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-docs.txt
mkdocs serve
```

然后打开 `http://127.0.0.1:8000/`。

## 直接预览

如果暂时不安装 MkDocs，可打开 `site_preview/index.html` 查看本次生成的静态预览。预览版用于审阅内容；正式网站应使用 `mkdocs serve/build`。
