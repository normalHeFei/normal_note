### config
- 几个注解的用法

1. @ConfigurationProperties: 定义配置类, 配置类会作为普通的java bean, 需要配合以下两个注解使用
2. @EnableConfigurationProperties([YourProperties].class):  启用配置类, 有条件启用,配置自己的autoConfig
3. @ConfigurationPropertiesScan 定义扫描范围. 

