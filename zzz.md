# 目录 (至0306)

1. spring cloud 生态, spring alibaba,dubbo ,netty源码解析
2. 容器化 & 云原生k8s, 部署架构(torlib)
3. 项目总结. 

   0. zk统一配置(常见问题) & 营销活动抽象 & 多数据源统计
   1. torlib common内容: 分布式日志收集,中间件API适配. 缓存统一管理.
   2. 多线程(异步转同步), 事务一致性(配合开源实现), 规范客户化(条件加载). 外部接口调用统一封装 
4. 动态规划,递归,分治常见算法套路

# step one

## cap

c: 大意是存储系统的所有客户端请求，都能得到一个“说的过去”的响应。例如：A先写入1再写入2，B不能读到2之后又读到

a:存储系统的所有操作最终都返回成功。我们称系统是可用的。

p(分区容忍): 如果集群中的机器被分成了两部分，这两部分不能互相通信，系统是否能继续正常工作。

## nacos&zk脑裂问题

nacos 偏可用性,即AP,  zk 偏一致性, 即CP. 

## nacos集群一致性

##  sentinel哪些限流算法
## seata分布式事务原理

## rocketmq顺序消费,重复消费问题

## dubbo初始化时序图

## dubbo协议设计(2.0&3.0)

## dubbo以负载均衡为例,阐述扩展机制实现原理

## dubbo代理创建及其javasist应用

## netty线程模型,epoll

## autoconfig

# step two

## k8s

大体分为以下几个内容:

kubectl:  集群的控制中心

kubelet:  每个容器的管理者

kubeproxy: 每个容器的代理,负责路由与网络

api-server: k8s集群中的各个部分都是通过api-server交互

## torlib 部署架构

### nginx

### mycat













