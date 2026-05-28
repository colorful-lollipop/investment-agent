# 开源发布指南 —— How to Open Source This Project

## 1. 代码托管平台准备（GitHub）

### 1.1 创建仓库

1. 登录 [GitHub](https://github.com)
2. 点击 **New Repository**
3. 填写信息：
   - Repository name: `investment-agent`
   - Description: `A modular quantitative investment analysis framework`
   - Visibility: **Public**
   - 勾选 Add README（已有，可忽略）
   - 选择 License: **MIT**
4. 点击 **Create repository**

### 1.2 推送本地代码

```bash
git init
git add .
git commit -m "feat: initial release of investment agent v0.1.0"
git branch -M main
git remote add origin https://github.com/yourusername/investment-agent.git
git push -u origin main
```

## 2. 配置仓库设置

进入仓库 **Settings** 页面：

### 2.1 General

- **Topics**: 添加标签 `quant`, `quantitative`, `trading`, `backtest`, `a-share`, `python`, `machine-learning`
- **Social preview**: 上传项目封面图（可选，推荐 1280×640）
- **Discussions**: 开启（用于社区问答）

### 2.2 Branches

- 设置 **Branch protection rules** for `main`:
  - ☑ Require a pull request before merging
  - ☑ Require status checks to pass before merging
  - ☑ Require branches to be up to date before merging
  - 选择 CI workflow `ci`

### 2.3 Secrets and Variables

如果需要发布到 PyPI，后续添加 `PYPI_API_TOKEN`。

## 3. 首次发布（GitHub Release）

### 3.1 打 Tag（语义化版本）

```bash
git tag -a v0.1.0 -m "Release v0.1.0 - Initial release"
git push origin v0.1.0
```

### 3.2 创建 GitHub Release

1. 进入仓库 → **Releases** → **Draft a new release**
2. 选择 tag `v0.1.0`
3. Release title: `v0.1.0`
4. 内容参考 `CHANGELOG.md`
5. 点击 **Publish release**

## 4. 发布到 PyPI

### 4.1 注册 PyPI 账号

前往 [pypi.org](https://pypi.org) 注册账号，并生成 API Token。

### 4.2 使用 GitHub Actions 自动发布

在仓库 Settings → Secrets → Actions 中添加：
- `PYPI_API_TOKEN`: 你的 PyPI API Token

创建 `.github/workflows/release.yml`：

```yaml
name: Release

on:
  release:
    types: [published]

jobs:
  pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install build tools
        run: pip install build twine
      - name: Build package
        run: python -m build
      - name: Upload to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

### 4.3 手动发布（备选）

```bash
pip install build twine
python -m build
 twine upload dist/*
```

## 5. 推广与社区建设

### 5.1 内容平台发布

- **V2EX**: 在「分享创造」板块发布
- **知乎**: 写一篇「从零搭建量化投资Agent」的技术文章
- **简书/CSDN/掘金**: 发布项目介绍和使用教程
- **雪球/集思录**: 面向投资者社区介绍（注意合规提示）

### 5.2 技术社区

- **Reddit**: r/algotrading, r/quant, r/Python
- **Hacker News**: Show HN 帖子
- **Twitter/X**: 用线程形式介绍项目亮点

### 5.3 国内社区

- **GitHub中文社区**: helloGitHub
- **Gitee**: 同步镜像（国内访问更快）
- **微信公众号/小程序**: 技术文章引流

## 6. 持续维护清单

| 频率 | 事项 |
|------|------|
| 每次 PR | 代码审查、CI通过、更新 CHANGELOG |
| 每月 | 回复 Issues、合并依赖更新（Dependabot） |
| 每季度 | 发布新版本、更新文档、社区互动 |
| 每年 | 评估技术债、大版本升级、安全审计 |

## 7. 合规与法律注意事项

- ⚠️ **必须在 README 显著位置标注**: "本项目仅供研究学习，不构成投资建议"
- ⚠️ **A股实盘交易**: 需要证券从业资质或合规审查（仅提供框架，不承担交易责任）
- ⚠️ **数据来源**: 确保 akshare 等第三方数据使用符合其服务条款
- ✅ **License**: MIT License 已允许商业使用，但需保留版权声明

## 8. 下一步扩展建议

1. **文档站点**: 用 Sphinx + ReadTheDocs 搭建在线文档
2. **Docker 镜像**: 提供 `docker run` 一键启动
3. **Web UI**: 用 Streamlit / Gradio 提供可视化界面
4. **更多数据源**: 接入 Yahoo Finance、Binance、CTP 等
5. **策略市场**: 社区分享策略的插件机制

---

> 记住：开源不仅是代码公开，更是建立可持续的社区生态。保持透明、友善、专业的态度，你的项目会自然生长。
