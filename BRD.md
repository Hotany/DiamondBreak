1. 项目背景
解决青少年棒球训练中“战术理解”碎片化的问题。通过一个轻量级的 Web 工具，让小朋友在手机/iPad 上通过“模拟实战局面”进行点点划划的练习，从而提升 Baseball IQ。

2. 目标用户
球员（主要）：小学至初中阶段棒球队员，需要练习战术判断。

教练/家长（次要）：用于讲解战术或通过 App 考评孩子的理解程度。

3. MVP 核心功能范围 (Scope)
为了快速跑通，MVP 只包含以下三个核心模块：

A. 局面展示墙 (Scenario Dashboard)
从本地的excel表格中读取 100 个局面。

支持按 Category（如：一垒有人、满垒）进行筛选。

点击卡片进入具体的战术练习页。

B. 交互式战术板 (Interactive Tactical Board)
底图加载：使用用户提供的 printable-baseball-field-diagram.png。

手写板功能：小朋友可以在图上自由画线（模拟球路或传球路径）。

一键清除：方便重画。

C. 解析与反馈 (Analysis & Feedback)
隐藏式答案：默认隐藏 Correct Answer 和 Coach's Tip，点击按钮后展开。

自测闭环：小朋友画完后，自行比对解析。

4. 业务流程 (Business Process)
数据维护：管理员在 Google Sheets 中更新 Excel 条目。

内容加载：Streamlit 启动时通过 API 抓取最新数据。

用户练习：

用户选择一个场景（如 004 号）。

阅读“局面描述”和“向你提问”。

在战术底图上画出答案。

点击“查看解析”，学习教练的思维逻辑。

5. 技术栈要求 (Tech Stack)
前端/后端：Streamlit (Python)。

数据库：初期数据来源于excel表格，本地创建轻量级的数据库即可。如SQLite。

核心组件：streamlit-drawable-canvas（实现绘图功能）。

部署：Streamlit Cloud (GitHub 集成)。

6. MVP 成功指标
开发耗时：使用 Trae 配合此 BRD，在 2 小时内完成第一个可运行版本。

数据一致性：excel表格修改后，App 刷新即可同步。

可用性：在手机浏览器上能流畅画线并看清文字。
