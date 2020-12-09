### 并发基础概念 


- volatile 

1.保证可见性, 不保证原子性, 原子性有CAS 配合自旋实现. **避免重排序**.指令重排只有在 多核及其不存在数据依赖(如两个独立的赋值语句)的情况下cpu 才会进行指令重拍

可见性： 

    产生原因： 线程自己存在自己的工作内存，读取时会将主内存中的变量读到工作内存。多个线程各自读写时就会存在不一致的问题。

原子性：

    不保证的原因：举例说明：比如i++, 是个复合操作，同一时间，不同线程读取的可能是相同的值，这种情况，当a线程已经写完，但b线程之前已经读了，故还是原来的值，产生覆盖


重排序： 

    多核环境下，如果语句之间不存在数据的依赖性的话，编译器|处理器 考虑到性能因素可能会进行指令重拍, volatile 可以借助于内存屏障禁止指令重排 （屏障简单来讲就是起到阻塞的作用，保证顺序，与栅栏一个概念）
    


- CAS

通过cpu 原子指令(cmpxchg) 配合 volatile 可见性实现. 

**CAS 的ABA 问题**

添加时间戳或版本号. 

- 内存屏障 

 内存屏障是CPU或编译器提供的避免指令重排的一系列特殊指令(fence),能保证fence 指令前的load/store(读写指令)在fence 指令后的load/store(读写) 操作之前执行. 

- CPU的缓存模型

1. L1 core 独享, L2 两个 core 共享, L3 是所有core 共享, cpu 的cache 主要缓存指令
https://zhuanlan.zhihu.com/p/48157076

- unsafe 类相关方法

1. 类的非常规实例化: 只有 含参数 构造器的对象的初始化. 如GSON 构造对象, 可通过UnSafe.allocateInstance 实例化对象

2. 内存屏障支持 

UnSafe.loadFence
UnSafe.storeFence
UnSafe.fullFence

3. 分配堆外内存

如 netty 中的 BtyeBuffer.allocateDirect > DirectByteBuffer 

**直接分配内存详解**

创建一个 DirectByteBuffer 的时候,主要做这些事情: 1. 调用UnSafe.allocateDirect 分配内存. 2. 创建一个Cleaner, Cleaner 可以理解成DirectByteBuffer 的一个封装, 包含一个DirectByteBuffer 引用, 同时它还是一个虚引用. 这也就意味着如果这个 byteBuffer 被VM回收的话,会将这个虚引用放到引用队列(*注: 引用队列本身并未实现队列的相关功能. 其入队出队列功能实际上还是依赖操作Reference 的 next 指向实现的*)里 (这里的虚引用其实就是Cleaner),此外创建引用会启动一个ReferenceHandler daemon 线程, 会从引用队列里面拿到被虚拟机回收的引用,如果这个引用是Cleaner 的话, 则回调它的clean 方法, clean 方法最终调用的是UnSafe.的 freeMemory 方法

 

### 应用层面

#### Atomic 类

- 详细介绍
1. 初始化静态块获取被包装value(volatile修饰)的偏移量 valueOffset.
2. compareAndSwapObject(this, valueOffset, expect, update): 通过当前对象(this),和在 主内存中的对象地址 valueOffset 来获取实际最新的值, expect 是当前值, update 是待更新值, 配合自旋和volatile 可见性来实现原子更新
3. getAndSet: cas 配合自旋设值

####  AQS 类 

- 预备知识

java 的同步队列为 CLH 队列的 变种, 以下先介绍 CLH 队列, 直接看代码

特点: 在线程本地变量(栈)上自旋, 减少cpu 缓存同步 

```
    static class CLHLock {
        private ThreadLocal<Node> pre =  new ThreadLocal<>();
        private ThreadLocal<Node> curr = ThreadLocal.withInitial(Node::new);
        private AtomicReference<Node> tail = new AtomicReference<>(new Node());

        public CLHLock() {
        }

        public void lock() {
            Node curr = this.curr.get();
            //设置当前节点状态
            curr.lock = true;
            //队尾指针 指向新进来的线程对应的当前节点
            //tail get 返回的是之前阻塞的节点
            Node preLockNode = tail.getAndSet(curr);
            //当前节点的前置节点设置为之前的阻塞节点
            pre.set(preLockNode);
            //根据之前节点的状态自旋
            for (; pre.get().lock ; ) {

            }
        }

        public void unlock() {
            this.curr.get().lock = false;
            //已解锁节点 出队列?
            curr.set(pre.get());
        }
    }
```

- 正式介绍

1. Node: 对于并发访问线程的包装, 包含前驱和后继节点及其本身等待的一个状态(waitStatus), 以及锁资源状态 state(int)

waitStatus: 

CANCEL(1): 在队列中等待的线程被中断或取消. 这类节点会被移除队列
**SIGNAL(-1)**: 表示当前节点的后继节点处于阻塞状态,需要被我唤醒
CONDITION(-2): 表示本身再 **等待队列** 中, 等待一个condition, 当其他线程调用condition.signal 方法时,才会将这样的节点放置在同步队列中
PROPAGATE(-3): 共享模式下使用,表示在可运行状态. 
0:  初始化状态

从入口代码开始

```
    public final void acquire(int arg) {
        //尝试获取锁
    if (!tryAcquire(arg) &&
        //没获取到的话,放入队列, 并且再队列里自旋获取锁资源(acquireQueued)
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        //如果等待途中被中断,则恢复中断 
        selfInterrupt();
    }

     
     private Node addWaiter(Node mode) {
        Node node = new Node(Thread.currentThread(), mode);
        // Try the fast path of enq; backup to full enq on failure
        Node pred = tail;
        if (pred != null) {
            //调整新入队节点的前置指针
            node.prev = pred;
            //调整尾指针指向新入队的节点, 并发故用cas 
            if (compareAndSetTail(pred, node)) {
                pred.next = node;
                return node;
            }
        }
        //自旋入队
        enq(node);
        return node;
    }

    **关键方法**
    final boolean acquireQueued(final Node node, int arg) {
        boolean failed = true;
        try {
            boolean interrupted = false;
            //自旋 判断前驱节点是不是头结点, 即判断 是不是轮到我来竞争资源了
            for (;;) {
                final Node p = node.predecessor();
                //如果是并且成功获取了资源, 调整指针, 设置队头是当前节点
                if (p == head && tryAcquire(arg)) {
                    setHead(node);
                    p.next = null; // help GC
                    failed = false;
                    return interrupted;
                }
                //如果还没轮到我,检查一下我的前置节点是不是 signal 状态, 如果不是说明他不会通知我
                //我需要再向前寻找 状态 是 signal 的节点并且排到他的后面 
                if (shouldParkAfterFailedAcquire(p, node) &&
                    parkAndCheckInterrupt())
                    interrupted = true;
            }
        } finally {
            if (failed)
                cancelAcquire(node);
        }
    }


    private static boolean shouldParkAfterFailedAcquire(Node pred, Node node) {
        int ws = pred.waitStatus;
        if (ws == Node.SIGNAL)
            /*
             * This node has already set status asking a release
             * to signal it, so it can safely park.
             */
            return true;
        if (ws > 0) {
            /*
             * Predecessor was cancelled. Skip over predecessors and
             * indicate retry.
             */
            do {
                node.prev = pred = pred.prev;
            } while (pred.waitStatus > 0);
            pred.next = node;
        } else {
            /*
             * waitStatus must be 0 or PROPAGATE.  Indicate that we
             * need a signal, but don't park yet.  Caller will need to
             * retry to make sure it cannot acquire before parking.
             */
             //设置之前正常的节点,状态为SIGNAL. 
            compareAndSetWaitStatus(pred, ws, Node.SIGNAL);
        }
        return false;
    }

    public final boolean release(int arg) {
        if (tryRelease(arg)) {
            Node h = head;
            if (h != null && h.waitStatus != 0)
                unparkSuccessor(h);
            return true;
        }
        return false;
    }

     //从头结点开始查找下一个需要唤醒的就"非取消" 节点
     private void unparkSuccessor(Node node) {
        /*
         * If status is negative (i.e., possibly needing signal) try
         * to clear in anticipation of signalling.  It is OK if this
         * fails or if status is changed by waiting thread.
         */
        int ws = node.waitStatus;
        if (ws < 0)
            compareAndSetWaitStatus(node, ws, 0);

        /*
         * Thread to unpark is held in successor, which is normally
         * just the next node.  But if cancelled or apparently null,
         * traverse backwards from tail to find the actual
         * non-cancelled successor.
         */
        Node s = node.next;
        if (s == null || s.waitStatus > 0) {
            s = null;
            // 第一次没找到的话, 从队尾开始找
            for (Node t = tail; t != null && t != node; t = t.prev)
                if (t.waitStatus <= 0)
                    s = t;
        }
        if (s != null)
            LockSupport.unpark(s.thread);
    }
```

- AQS 实现总结

线程封装节点包含 代表锁资源的state 变量. 和代表阻塞线程当前状态的 waitState. 

通过模板方法 acquire 和 release  以及 子类的tryAcquire 和 tryRelease 方法 获取和释放 多线程竞争资源

acquire 和 release 主要逻辑:

acquire 判断是否成功获取锁资源. 如果未获取资源,入队并自旋等待(park,*是否等待需要判断前置节点的waitStatus 是否为signal, 如果不是需要调整入队等待节点的前置节点*), 前置节点调用unpark 方法唤醒.

release 从队头开始, 调用tryRelease 如果头节点成功释放了竞争资源, 通过 unpark 方法唤醒后继剩余节点 




### 并发集合 & 常见问题

-  ConcurrentModifiyExeception

应该从 迭代器的角度来理解这个异常。为了避免在迭代过程中被并发修改如果迭代过程中发现有修改情况，就会立刻快速失败（fast fail). 这个异常其实是为了保证 多线程环境下的正常的迭代操作

产生原因： 

for 迭代时其实是调用 list 的 Intr 迭代器进行迭代。 Intr 内部保存了一个modCount 和 expectedModCount两个属性。 这两个初始值是相等的。add 或 remove 这些方法执行时会修改 modCount(+1)，迭代时会校验这两个值是否相等，不相等的话就报这个异常

解决办法： 

1. ~~迭代时加锁，用Collectors 包装一下~~
2. 用copyOnWriteArrayList

- 自旋锁  (spin lock)

> cas  + 循环 即叫自旋锁。


- synchronized 和 lock 有啥区别

1. sync 是属于jvm层面，lock属于api层面。 
2. sync 配合 notify 只能粗略唤醒线程，而 lock 配合 多个 condition 可以精确唤醒指定线程
3. lock 可以指定加锁是否公平，而sync则不行 

- ReentrantLock & condition 

> 可重入锁


- ReentrantReadWriteLock

> 读可以多个，写只有一个。常见应用场景：缓存


- 阻塞队列

可以代替原有 需要使用wait 和notify 实现的场景

常见使用实现类.

1. ArrayBlockingQueue: 有界基于 数组的queue
2. LinkedBlockingQueue 基于 链表 的queue 
3. SynchronousQueue: 不存储元素的队列

队列api记忆：

add/remove 满或空 抛异常
offer/poll 满或空 返回false
put/take   满或空阻塞



- 线程池

7个参数含义

1. int corePoolSize
核心线程数，也即正常情况工作线程数

2. int maximumPoolSize,
最大线程数

3. long keepAliveTime,
需要结合阻塞队列来理解：假设阻塞队列的长度是3，核心数是2，最大线程数是5. 运行时是这样的：大于核心数时，会放到阻塞队列里面排队，如果队列满了才会启用新的工作线程，直到达到最大线程数
当达到最大线程数时，如果此时submit到线程池的任务变慢了，核心线程能够应对工作的话，这时线程池会动态减少工作线程数到核心线程数。这里的keepAliveTime 就是指 除核心线程以外的那几个线程的空闲时间。如果大于这个参数所指定的，线程池则会回收这些线程

4. TimeUnit unit,
第三个参数的单位

5. BlockingQueue<Runnable> workQueue,
比核心线程数多出来的线程会进入阻塞队列排队。别用 Executors.newFixedThreadPool 方法构造， 默认指定的阻塞队列（LinkedBlockingQueue）大小是Integer.MAX_VALUE，需显示指定


6. ThreadFactory threadFactory,
用默认的就行，有需要的话区分下线程名字

7. RejectedExecutionHandler handler

拒绝策略：

AbortPolicy（默认）： 直接抛异常
DiscardPolicy： 随机丢弃
DiscardOldestPolicy： 丢弃最老的线程
CallerRunsPolicy：将执行权回退给调用者线程。 


线程池配多少个好

从经验上讲需要区分是cpu密集型还是io密集型。 cpu密集型的话，为了避免上下文切换，数量不宜过多，一般为cpu核数 + 1 ； 如果是io密集型的话，可以多点，一般为  cpu核数 * 10 大小

- 死锁编码和定位





