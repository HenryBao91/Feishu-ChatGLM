# Feishu-ChatGLM
🚀 Integrate ChatGLM-3-6B with Feishu App Bot to create an intelligent chatbot. Follow the steps to prepare the model and set up the Feishu application.
> Reference https://github.com/ConnectAI-E/Feishu-ChatGLM

## ✨ Function List
- [X] 飞书群中@`BOT_NAME`进行对话
- [X] 单聊、群聊自动记忆上下文
- [X] 使用 `/new` 命令开启新会话
- [X] 使用新飞书API接口
- [ ] 加入多模态模型，如 Stable-Diffusion

## Chat shot
![a](assets/chat.png)

## Local Deployment Method

### Step 1. 启动 chatGLM 的api
1. 此步骤可以在本机，也可以在服务器等其他机器，即 `src/chatglm_sever` 这个模块可以移至其他任何地方运行
2. 安装conda环境，切换conda环境（步骤略）
3. `cd ./src/chatglm_server`
4. `pip install -r requirements.txt`  安装 python 依赖包, pytorch 的安装会要比较长的时间
5. `python chatglm_server.py` 启动 chatGLM api 服务
6. 第一次启动需要下载 chatGLM 模型，时间会比较久，默认是 'THUDM/chatglm-6b-int4' 
7. 默认支持cpu、gpu、多卡gpu进行部署，一些参数的调整见脚本`server.py`的开头部分
8. 记录好部署ip地址和端口号（如果为本机和默认配置，则为 http://localhost:8000

详细流程见[ChatGLM官方Github](https://github.com/THUDM/ChatGLM-6B) 

