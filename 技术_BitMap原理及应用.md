### 预备知识

#### 单线程的reactor 模型
 
主要分为以下几个主要角色
- demultiplexer(多路复用器): **单线程**负责接收网络资源 (可用的 socket 连接)
- dispatcher(消息分发器):  可以理解成一个注册器,业务handler注册在其中.
- handler:  业务处理器

 多路复用器单线程轮询是否有可用的资源, 如果有的话,发送给分发器(dispatcher:可以理解成线程池?),一个线程执行一个类型的任务. 


> 

### 
- 扩展了线程池接口,可以简单理解成 ExecuteService , 并包含EventLoopGroup 引用 


