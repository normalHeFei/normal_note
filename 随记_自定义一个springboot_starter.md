### 使用

自定义一个starter，一般需要一个 properties config, 一个根据properties config的配置信息的配置类（configuration)。 configuration 通常设置为有条件的加载，比如根据classpath下有无某个类来决定是否加载这个configuration，配置启动类中一般是注册一些bean，为了能够让引用的人能够重新自定义bean， configuration里的bean定义需要用@conditionOnMissingBean来修饰。 

 ### 原理 

 