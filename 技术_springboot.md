> 记录使用springboot 过程中所遇到的问题及其解决办法

### 问题记录
- 打包成jar时，配置文件如何配置放在jar外目录

默认会读取jar所在目录下的config目录
命令行指定， java -jar app.jar --spring.config.location=file://

- 中文乱码

命令行启动时， java -Dfile.encoding=utf-8 -jar xxx.jar 


- 静态资源访问

```

String schema = System.getProperty("os.name").startsWith("Windows") ? "file:///" : "file:";
        logger.info("resourceLocations: {}", schema + postProperties.getUploadDir());
        registry.addResourceHandler("/static/**")
                //不一定时classpath下，打成fat jar 时，可以关联本地文件系统目录，注意最后 为"/"
                .addResourceLocations(schema + postProperties.getUploadDir() + File.separator)
                .setCacheControl(CacheControl.maxAge(1, TimeUnit.HOURS).cachePublic());

```


### config
- 几个注解的用法 dgbank888

1. @ConfigurationProperties: 定义配置类, 配置类会作为普通的java bean, 需要配合以下两个注解使用
2. @EnableConfigurationProperties([YourProperties].class):  启用配置类, 有条件启用,配置自己的autoConfig
3. @ConfigurationPropertiesScan 定义扫描范围. 


java -jar   normal_portal-0.0.1-SNAPSHOT.jar  -Dlogging.config=file:D:\projects\normal_portal\src\main\resources\logback-spring.xml
- 问题

1. 启用auto config 后, 代码里如何自定义配置 ? 


### bean 的生命周期

1. 
