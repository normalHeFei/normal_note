> JUC包下有很多的工具类都是基于 AQS(AbstractQueuedSynchronizer) 实现. 故深刻理解这部分内容非常重要.
> 虽然从代码角度AQS只是一个模板类,但涉及的概念和细节特别多,避免遗忘,做个总结. 会持续补充

- AQS 实现原理
  
AQS 是由一个双端链表构成, 每个节点(Node)包含指向前后两个节点的指针(pre,next),一个代表当前竞争的资源状态(state),一个代表等待队列里面节点的等待状态(**waitStatus**)
关于等待状态的含义值,描述如下: 

waitStatus: 
1. CANCEL(1): 在队列中等待的线程被中断或取消. 这类节点会被移除队列
2. **SIGNAL(-1)**: 表示当前节点的后继节点处于阻塞状态,需要被我唤醒
3. CONDITION(-2): 表示本身再 **等待队列** 中, 等待一个condition, 当其他线程调用condition.signal 方法时,才会将这样的节点放置在同步队列中
4. PROPAGATE(-3): 共享模式下使用,表示在可运行状态. 
0:  初始化状态

重点分析以下几个方法

```
    public final void acquire(int arg) {
        //尝试获取资源
    if (!tryAcquire(arg) &&
        //没获取到的话,放入队列, 并且再队列里自旋获取锁资源(acquireQueued)
        acquireQueued(addWaiter(Node.EXCLUSIVE), arg))
        //如果等待途中被中断,则恢复中断 
        selfInterrupt();
    }

     //入等待队列
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

    **重要**
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

    //如果前置节点 waitStatus 是 signal 状态,则当前节点park 等待.
    // 否则向前查询,将当前节点排到最近的signal状态节点的后面
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

**AQS 实现原理再总结**
同步队列调用tryAcquire可重写方法来判断是否已经获取竞争资源,如果没有获取,就将当前线程包装成节点入队列
然后再自旋获取资源.是否自旋取决于前置节点的waitStatus,如果前置节点的waitStatus的状态是signal,则代表
当前节点需要parking等待,parkding等待的目的是为了减少cpu空转,但会增加线程上下文切换,因为parking的原理是将用户态数据转为内核态. 
后面unpark的操作则是将线程状态数据由内核态转为用户态. 等到前置节点release释放掉竞争状态后,后面的自旋判断就会竞争获取状态重复以上过程

画外音:AQS 其实是操作系统里面[管程](https://time.geekbang.org/column/article/86089) 模型的一种体现,将线程之间的同步
协助用一个同一个的对象来进行管理. AQS 中的waitStatus其实就是这种思想的体现. 

#### AQS 应用

>AQS 基础章节 介绍了AQS 模板类的原理,以下介绍下juc下面基于AQS实现的并发工具类,从而对自己实现AQS有些启发

1. ReentrantLock  & condition 

```
 默认的非公平实现: cas 获取竞争状态.设置当前独占线程. 公平版的则是入队列
    
   final boolean nonfairTryAcquire(int acquires) {
            final Thread current = Thread.currentThread();
            int c = getState();
            if (c == 0) {
                //如果还没有占用锁, cas 占用锁资源,并设置互斥线程 为自己
                if (compareAndSetState(0, acquires)) {
                    setExclusiveOwnerThread(current);
                    return true;
                }
            }
            //如果互斥线程已经是自己了,则增加重入次数
            else if (current == getExclusiveOwnerThread()) {
                int nextc = c + acquires;
                if (nextc < 0) // overflow
                    throw new Error("Maximum lock count exceeded");
                setState(nextc);
                return true;
            }
            return false;
        }
    //释放锁,则是减去需要释放的状态值并更新状态和独占线程
   protected final boolean tryRelease(int releases) {
            int c = getState() - releases;
            if (Thread.currentThread() != getExclusiveOwnerThread())
                throw new IllegalMonitorStateException();
            boolean free = false;
            if (c == 0) {
                free = true;
                setExclusiveOwnerThread(null);
            }
            setState(c);
            return free;
        } 

    
```
lock 的逻辑前面已经说过. 下面描述下  condition await/signal/signalAll 的实现机制

```
 public final void await() throws InterruptedException {
            if (Thread.interrupted())
                throw new InterruptedException();
            //ConditionObject 新增一类状态为conditional 状态的节点.
            //先添加到 每个条件的等待队列 (等待队列和阻塞队列是分开的, 是多对一的关系)
            //每个等待队列和一个线程相关联
            Node node = addConditionWaiter();
            //释放
            long savedState = fullyRelease(node);
            int interruptMode = 0;
            //如果不在之前提到的同步队列,则park, 
            //后续signal 会将conditional 节点加入 同步队列
            while (!isOnSyncQueue(node)) {
                LockSupport.park(this);
                if ((interruptMode = checkInterruptWhileWaiting(node)) != 0)
                    break;
            }
            if (acquireQueued(node, savedState) && interruptMode != THROW_IE)
                interruptMode = REINTERRUPT;
            if (node.nextWaiter != null) // clean up if cancelled
                unlinkCancelledWaiters();
            if (interruptMode != 0)
                reportInterruptAfterWait(interruptMode);
        }
``` 

2. ReentrantReadWriteLock
> 读写锁实现中, 一个整型32位代表锁状态,前16位代表读锁数, 后16位代表写锁

readLock.lock实现

```
protected final int tryAcquireShared(int unused) {
            Thread current = Thread.currentThread();
            int c = getState();
            //如果已经有写锁了并且不是自己,则直接返回
            if (exclusiveCount(c) != 0 &&
                getExclusiveOwnerThread() != current)
                return -1;
            int r = sharedCount(c);
            //公平和非公平实现读是否阻塞稍后分析
            if (!readerShouldBlock() &&
                r < MAX_COUNT &&
                //如果不需要阻塞,则cas 加上要读锁个数 c, SHARED_UNIT为2进制的16左移一位,即第17位为1其它位都为0
                //故  c + SHARED_UNIT 简单的 +c 
                compareAndSetState(c, c + SHARED_UNIT)) {
                if (r == 0) {
                    firstReader = current;
                    firstReaderHoldCount = 1;
                } else if (firstReader == current) {
                    firstReaderHoldCount++;
                } else {
                    HoldCounter rh = cachedHoldCounter;
                    if (rh == null || rh.tid != getThreadId(current))
                        cachedHoldCounter = rh = readHolds.get();
                    else if (rh.count == 0)
                        readHolds.set(rh);
                    rh.count++;
                }
                return 1;
            }
            return fullTryAcquireShared(current);
}
```

writeLock.lock 实现 

```

protected final boolean tryAcquire(int acquires) {
        
            Thread current = Thread.currentThread();
            int c = getState();
            //取低位16位值.也即写锁的个数
            int w = exclusiveCount(c);
            //代表已经有读锁或写锁存在
            if (c != 0) {
                // (Note: if c != 0 and w == 0 then shared count != 0)
                //如果写锁为0, 或者独占线程不是自己,则直接失败. 
                // c!=0 并且 w = 0 代表,此刻有读但没有写,有读的时候不允许写,故直接返回false
                if (w == 0 || current != getExclusiveOwnerThread())
                    return false;
                //重入不能超过最大次数. 
                if (w + exclusiveCount(acquires) > MAX_COUNT)
                    throw new Error("Maximum lock count exceeded");
                // Reentrant acquire
                setState(c + acquires);
                return true;
            }
            // fair 的写阻塞策略则是老老实实排队.如果前面没有等待节点的话,则不阻塞
            // unfair 的写阻塞策略是不阻塞,直接竞争 
            if (writerShouldBlock() ||
                !compareAndSetState(c, c + acquires))
                return false;
            setExclusiveOwnerThread(current);
            return true;
}

```
readLock 逻辑

```
 protected final int tryAcquireShared(int unused) {
            Thread current = Thread.currentThread();
            int c = getState();
            //有写存在,并且不是自己直接返回. 
            if (exclusiveCount(c) != 0 &&
                getExclusiveOwnerThread() != current)
                return -1;
            //读未阻塞并且没有超过高位16位最大值并且cas增加读的个数成功的话,则获取到读锁
            int r = sharedCount(c);
            if (!readerShouldBlock() &&
                r < MAX_COUNT &&
                compareAndSetState(c, c + SHARED_UNIT)) {
                if (r == 0) {
                    //设置第一个读的线程
                    firstReader = current;
                    //初始化第一个读线程的重入数
                    firstReaderHoldCount = 1;
                } else if (firstReader == current) {
                    //增加第一个读线程的重入数
                    firstReaderHoldCount++;
                } else {
                    //以下则是其他的读线程逻辑:
                    //cachedHoldCounter 是最后一个读线程的重入数
                    HoldCounter rh = cachedHoldCounter;
                    //cachedHoldCounter 始终存储最后一个读线程的重入数
                    if (rh == null || rh.tid != getThreadId(current))
                        cachedHoldCounter = rh = readHolds.get();
                    else if (rh.count == 0)
                        readHolds.set(rh);
                   //读重入数++                     
                    rh.count++;
                }
                return 1;
            }
            return fullTryAcquireShared(current);
}

```

**读写锁的注意点**

默认的unfair策略 读写读 场景, 第二个读不会因为自己是读锁就获取读锁. 因为读的时候不能写, 为了避免写饥渴, 如果读前面是写的话,需要等前面的写做完以后才能读.

```
  final boolean apparentlyFirstQueuedIsExclusive() {
        Node h, s;
        return (h = head) != null &&
            (s = h.next)  != null &&
            //前面一个如果是写的话,读就会排队阻塞
            !s.isShared()         &&
            s.thread != null;
    }

```
3. countDownLatch 实现

await 方法

```
private static final class Sync extends AbstractQueuedSynchronizer {
        private static final long serialVersionUID = 4982264981922014374L;

        Sync(int count) {
            setState(count);
        }

        int getCount() {
            return getState();
        }

        // await方法等待,会回调这个方法. 当count降为0的时,不阻塞,故返回大于0(1)
        protected int tryAcquireShared(int acquires) {
            return (getState() == 0) ? 1 : -1;
        }
        //countdown 回调这个方法, 故是state -1
        protected boolean tryReleaseShared(int releases) {
            // Decrement count; signal when transition to zero
            for (;;) {
                int c = getState();
                //已经减为0,已经全部释放,直接放回false
                if (c == 0)
                    return false;
                int nextc = c-1;
                //cas 设置 减掉的 count.count = 0 则唤醒await 
                if (compareAndSetState(c, nextc))
                    return nextc == 0;
            }
        }
    }


```







