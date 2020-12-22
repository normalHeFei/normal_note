#### Atomic 类

- 详细介绍
1. 初始化静态块获取被包装value(volatile修饰)的偏移量 valueOffset.
2. compareAndSwapObject(this, valueOffset, expect, update): 通过当前对象(this),和在 主内存中的对象地址 valueOffset 来获取实际最新的值, expect 是当前值, update 是待更新值, 配合自旋和volatile 可见性来实现原子更新
3. getAndSet: cas 配合自旋设值