# 摸鱼人日历插件
![](https://private-user-images.githubusercontent.com/37870767/411299021-ead4c551-fc3c-48f7-a6f7-afbfdb820512.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDE3NjMwNDUsIm5iZiI6MTc0MTc2Mjc0NSwicGF0aCI6Ii8zNzg3MDc2Ny80MTEyOTkwMjEtZWFkNGM1NTEtZmMzYy00OGY3LWE2ZjctYWZiZmRiODIwNTEyLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMTIlMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzEyVDA2NTkwNVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTNiNGYyZTgxMjFjOWMwZmFkMTQ1NDFhNjhiZDQwZWJiYjg1NDdmYmZkMDNlYTUwOWE3MDFiOTMwNzM5NWFjOTEmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.MXqbLD4Rbn-LJsONC1os5DGpCFTKnQ8uEZnl3D8H0B8)

一个功能完善的 AstrBot 摸鱼人日历插件，支持精确定时发送、多群组不同时间设置、自定义触发词，并提供多种精美排版样式。

## 功能特点

- 🎯 精确定时发送，无需轮询检测
- 🌟 支持多群组不同时间设置
- 🔧 支持自定义触发词（默认为"摸鱼"）
- 🎨 提供多种精美排版样式，每次随机选择
- ⚡ 支持立即发送功能
- 🔄 自动备份异常配置文件
- 🌐 多API源支持，自动故障转移（指两个，其中一个还偶尔抽风）
- 🕒 显示下一次发送的等待时间
- 📝 支持通过配置文件自定义API端点和消息模板

## 使用说明

### 命令列表

- `/set_time HH:MM` - 设置发送时间，格式为24小时制
  - 例如：`/set_time 09:30` 或 `/set_time 0930`
  - 设置成功后会显示下一次发送的等待时间
- `/reset_time` - 取消当前群聊的定时设置（触发词仍可使用）
- `/list_time` - 查看当前群聊的时间设置与触发词
- `/execute_now` - 立即发送摸鱼人日历
- `/set_trigger 触发词` - 设置触发词，默认为"摸鱼"

### 触发方式

1. 定时发送：在设定的时间自动发送
2. 触发词发送：检测到触发词时发送
3. 手动发送：使用 `/execute_now` 命令立即发送

### 配置文件

插件现在支持通过`_conf_schema.json`配置文件自定义以下设置：

- API端点列表：按优先顺序排列，自动故障转移
- 消息模板：支持多种排版样式，每次随机选择
- 默认模板：当没有其他模板可用时使用
- 请求超时时间：API请求的超时设置

用户可以通过AstrBot控制台的配置管理界面修改这些配置。

## 常见问题

Q: 为什么显示获取图片失败？  
A: 插件使用了多个备用API源，如果都获取失败，可能是：
1. 在配置里增加超时时间
2. 网络连接问题
3. API服务暂时不可用
4. 如果持续失败，请提交 issue 或联系作者更换API源

Q: 为什么默认的触发词发送检测不到？  
A: 请检查该群聊是否设置过时间或者触发词，如果没有设置过此群聊的消息并不在监听返回。设置后即可恢复正常

Q：样式我不喜欢怎么办，不想让他随机，我想固定一个样式，可以吗？  
A：可以的，你现在可以在AstrBot控制台的配置界面中编辑模板列表，只保留你喜欢的模板即可。

## 更新日志

### v2.3.3
- 由于随机模版重复率过高，更改为每次按顺序发送

### v2.3.2
- 🔄 优化API端点调用逻辑，按配置顺序依次尝试
- 🐛 修复模板随机选择的问题
- 🎨 优化日志输出，移除冗余调试信息
- ⚡ 改进图片下载处理逻辑
- 📝 增加api超时时间

### v2.3.0
- ✨ 新增多API源支持，自动故障转移
- 🎨 支持自定义消息模板
- 🔧 优化配置文件结构
- 📝 完善错误日志

### v2.2.0
- 添加配置文件`_conf_schema.json`，支持自定义API端点和消息模板
- 移除独立的templates.json文件，整合到配置系统中
- 优化消息创建逻辑，直接返回MessageChain
- 提高代码复用性和可维护性
- 更新文档，添加配置说明

### v2.1.0
- 优化消息发送机制
- 改进 `/reset_time` 命令，现在会从任务队列中删除对应任务
- 添加等待时间显示，设置时间后会显示下一次发送的等待时间
- 优化错误处理和日志记录
- 改进消息格式，添加表情符号使消息更友好

### v2.0.0
- 重构代码结构，提高可维护性
- 添加多API源支持，提高可用性
- 优化错误处理机制
- 添加配置文件自动备份功能
- 新增多种排版样式
- 改进定时器实现，提高精确度

## 支持与反馈

- 提交 Issue：[GitHub Issues](https://github.com/quirrel-zh/astrbot_plugin_moyuren/issues)
- 联系作者：可在群聊中搜索 quirrel-zh
- 帮助文档：[AstrBot 官方文档](https://astrbot.app/dev/plugin.html)
