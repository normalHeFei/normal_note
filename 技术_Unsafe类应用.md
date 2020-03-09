
### 功能
1. 分配直接内存
2. CAS

#### 分配直接内存

- 应用: BtyeBuffer.allocateDirect > DirectByteBuffer
**直接分配内存详解**
1. 创建一个 DirectByteBuffer 的时候,主要做这些事情: 1. 调用UnSafe.allocateDirect 分配内存. 2. 创建一个Cleaner, Cleaner 可以理解成DirectByteBuffer 的一个封装, 包含一个DirectByteBuffer 引用, 同时它还是一个虚引用. 这也就意味着如果这个 byteBuffer 被VM回收的话,会将这个虚引用放到引用队列里 (这里的虚引用其实就是Cleaner),此外创建引用会启动一个ReferenceHandler daemon 线程, 会从引用队列里面拿到被虚拟机回收的引用,如果这个引用是Cleaner 的话, 则回调它的clean 方法, clean 方法最终调用的是UnSafe.的 freeMemory 方法

**注**:
- 引用队列本身并为实现队列的相关功能. 其入队出队列功能实际上还是依赖操作Reference 的 next 指向实现的


#### CAS
1. 通过cpu 原子指令(cmpxchg) 配合 volatile 可见性实现
**CAS 的ABA 问题**
1. 添加时间戳或版本号. 


#### 类的非常规实例化
**应用**
1. 只有 含参数 构造器的对象的初始化. 如GSON 构造对象, 可通过UnSafe.allocateInstance 实例化对象

#### 内存屏障
**内存屏障是CPU或编译器提供的避免指令重排的一系列特殊指令(load/store),规定这种指令前后的读写指令得顺序执行**

1. UnSafe.loadFence
2. UnSafe.storeFence
3. UnSafe.fullFence

