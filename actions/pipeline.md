# GitHub Actions 闭环草案

名称：进化基因流水线

触发方式：
- 手动触发
- Gist 或任务文件更新触发
- 定时触发

流程：
1. 拉取任务
2. 安装依赖
3. 调用 GitHub API 搜索项目
4. 拉取候选项目元数据
5. 生成研究摘要
6. 运行最小代码验证
7. 输出成果到 inbox
8. 本地 Hermes 拉取并复核

Secrets：
- GITHUB_TOKEN：GitHub 自动令牌或细粒度令牌（GitHub API / Actions 用）
- GPT55_5YUANTOKEN_API_KEY：主脑密钥
- DEEPSEEK_V4_FLASH_API_KEY：辅助脑密钥
- MINIMAX_M27_HIGHSPEED_API_KEY：辅助脑密钥

注意：所有 Secrets 只在 GitHub 环境中读取，不写入仓库。
