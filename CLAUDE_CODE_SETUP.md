# Claude Code 启动指南

## 一、安装 Claude Code

Claude Code 是 Anthropic 官方的命令行工具，需要 Node.js 18+。

```bash
# 用 npm 全局安装
npm install -g @anthropic-ai/claude-code

# 验证安装
claude --version
```

首次运行时会让你登录 Anthropic 账号（用你的 Claude.ai 账号即可）。

## 二、设置项目

```bash
# 1. 创建项目目录
mkdir multi-agent-code-reviewer
cd multi-agent-code-reviewer

# 2. 把 CLAUDE.md 和 WEEK1_TASKS.md 放到项目根目录
# （从这次对话下载这两个文件，放进来）

# 3. 初始化 git
git init
git branch -M main

# 4. 启动 Claude Code
claude
```

## 三、首次对话开场白

Claude Code 启动后，第一句话就发下面这段，它会自动读取 CLAUDE.md 建立上下文：

```
请先读 CLAUDE.md 和 WEEK1_TASKS.md，了解这个项目的背景、范围和我本周的任务。

读完后简要告诉我：
1. 你理解的项目定位
2. 本周我应该做什么
3. 本周明确不做什么

然后我们开始 Day 1 的任务。
```

## 四、日常使用节奏

### 每天开工
```
继续项目。请回顾 CLAUDE.md 和 WEEK1_TASKS.md，
今天是 Day X (日期)，我要做今天的任务。
```

### 遇到卡壳
Claude Code 可以直接读你的代码、跑命令、看报错。直接把错误贴给它，不要先 google。

### 每天收工
```
今天做完了 X、Y、Z。帮我：
1. 生成一个规范的 git commit message
2. 更新 README 的进度条
3. 列一下明天 Day X+1 要做的事
```

## 五、Claude Code 关键技巧

1. **让它写 test**：每写一个模块，跟它说"给这个模块写 pytest 测试"
2. **让它读文档**：遇到新库，让它帮你读官方文档总结核心用法
3. **让它改不让它重写**：你的偏好是简洁节约 Token，所以总是说"修改这个文件"而不是"生成新文件"
4. **用 `/clear` 清理历史**：长对话占 Token，一个任务做完可以 /clear 重新开始

## 六、成本预估

按 Claude Sonnet 4 当前定价：
- **Claude Code 用量**：一个月开发约 $20-50
- **项目里调用 Claude API**：用 Haiku 做 Reviewer，一个月 $10-30 够了
- **总预算**：**< $100**

如果你有 Claude Pro 订阅，Claude Code 已经包含在内，不额外收费。

## 七、如果没有 Claude Code

退而求其次的选择：
1. **Cursor + Claude Sonnet 4**：IDE 集成，效果接近 Claude Code
2. **VS Code + Continue 插件 + Claude API**：免费但手动
3. **继续用 Claude.ai 网页版**：每段代码复制粘贴，效率低但能用

Claude Code 是最推荐的，单项目 100 刀买一个月高效开发太值了。

---

## ⚠️ 一个重要提醒

Claude Code 每次启动是**全新会话**，它只"记得" CLAUDE.md 里的内容。所以：

- **重要决策写进 CLAUDE.md**：比如"不用 K8s"、"Embedding 用 BGE-M3"
- **每周更新 CLAUDE.md 里的进度**：Week 1 做完后，在里面加一行"✅ Week 1 已完成：xxx"
- **代码规范也写进去**：比如"函数名用 snake_case，类名用 PascalCase"

这样下周开新会话时，Claude Code 立刻能接上，不用你再重复说。
