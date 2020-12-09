> JUC包下有很多的工具类都是基于 AQS(AbstractQueuedSynchronizer) 实现. 故深刻理解这部分内容非常重要.
> 虽然从

AQS 是由一个双端链表构成, 每个节点(Node)包含指向前后两个节点的指针(pre,next),一个代表当前竞争的资源状态(state),一个代表等待队列里面节点的等待状态(**waitStatus**)
关于等待状态的含义值,描述如下: 

waitStatus: 
1. CANCEL(1): 在队列中等待的线程被中断或取消. 这类节点会被移除队列
2. **SIGNAL(-1)**: 表示当前节点的后继节点处于阻塞状态,需要被我唤醒
3. CONDITION(-2): 表示本身再 **等待队列** 中, 等待一个condition, 当其他线程调用condition.signal 方法时,才会将这样的节点放置在同步队列中
4. PROPAGATE(-3): 共享模式下使用,表示在可运行状态. 
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
    /**
    * 在队列里自旋查看能够获取资源,但是也不是一直自旋, 如果线程很多,一直自旋会消耗cpu资源,
      对于前置节点 的waitStatus是 Signal 的话,就意味着我需要parking(parking操作会将上下文由用户态转化为内核态,频繁park/unpark会增多上下文切换)
    */
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

**AQS 实现总结**

AQS 其实是


### 应用层面

#### AQS 应用

>AQS 基础章节 介绍了AQS 模板类的原理,以下介绍下juc下面基于AQS实现的并发工具类,从而对自己实现AQS有些启发

#### Atomic 类

- 详细介绍
1. 初始化静态块获取被包装value(volatile修饰)的偏移量 valueOffset.
2. compareAndSwapObject(this, valueOffset, expect, update): 通过当前对象(this),和在 主内存中的对象地址 valueOffset 来获取实际最新的值, expect 是当前值, update 是待更新值, 配合自旋和volatile 可见性来实现原子更新
3. getAndSet: cas 配合自旋设值


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





