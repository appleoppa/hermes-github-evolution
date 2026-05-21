# Evolver + Evomap 闭环任务

目标：让 GitHub Actions 容器真实读取 GitHub 顶级公开项目，抽取可验证工程基因，写回 inbox / genes / research，供本地主脑验收后回流。

## 门禁

1. 必须使用 GitHub API 读取真实仓库元数据。
2. 每条 gene 必须包含来源仓库、采样文件路径、内容 hash、可复用机制、边界声明。
3. 远程 workflow 成功不等于进化完成；必须本地拉回并复核 JSON 内容。
4. 不打印、不写入任何 token 或模型密钥。
5. 没有真实采样文件时，不允许声称完成代码吸收。

## 当前主题

`ai agent eval harness autonomous coding workflows`
