> 经常有业务场景需要 reload 单例bean. 例如 运行时修改配置, 运行时重新注入接口的其他实现. 这里对此类技术的实现做一个调研.

### 可借鉴的几种实现及涉及知识点

1. spring cloud 的 @RefreshScope
2. 配置bean 包装成 mbean, 借助jmx统一管理
3. java -agent 参数指定.  -agent 参数可以指定一个类来处理字节码.提供了操作字节码的钩子. 可以利用这一点,监听文件变化,更新字节码.从而实现reload 的效果. 
4. osgi 
5. 
   

### 配置动态更新的简单实现

对于environment.getProperty() 形式的配置获取可以采取以下方法实现动态更新配置

1. 实现一个支持更新的 PropertySource 
2. 容器启动时 获取 ConfigurableEnvironment 实例, 将自定义支持更新的 PropertySource 放在ConfigurableEnvironment.propertySources 的最前头

原理说明:

environment.getProperty 最终会委托到 ConfigurableEnvironment.propertySources 的每一个 propertySource.getProperty 
只要给定的key 对应的value 找到了,则直接返回. 故只要在头部插入一个PropertySource 即可.

代码: 

```
 // 定义支持自动更新的PropertySource, 可以借助于zk,jmx,或者暴露一个接口给外面支持更新. 这里选择监听事件的方式
 public class AutoUpdatePropertySource extends PropertySource<Map<String, Object>> implements ApplicationListener<PropertyUpdateParam> {

    public AutoUpdatePropertySource(String name, Map<String, Object> source) {
        super(name, source);
    }

    @Override
    public Object getProperty(String name) {
        return source.get(name);
    }


    @Override
    public void onApplicationEvent(PropertyUpdateParam event) {
        int type = event.getType();
        if (type == 0) {
            source.put(event.getKey(), event.getValue());
            return;
        }
        if (type == 1) {
            source.put(event.getKey(), event.getValue());
            return;
        }
        if (type == 2) {
            source.remove(event.getKey());
            return;
        }

        logger.warn("event type unknow \t" + type);
    }
  }

 // 注册自定义 propertySource 
  @Bean
    public AutoUpdatePropertySource autoUpdatePropertySource(ConfigurableEnvironment environment) {
        MutablePropertySources propertySources = environment.getPropertySources();
        Iterator<PropertySource<?>> iterator = propertySources.iterator();
        Map map = new HashMap(32);
        for (; iterator.hasNext(); ) {
            PropertySource<?> next = iterator.next();
            if (next.getSource() instanceof Map) {
                map.putAll((Map) next.getSource());
            }
        }
        AutoUpdatePropertySource autoUpdatePropertySource = new AutoUpdatePropertySource("autoUpdatePropertySource", map);
        propertySources.addFirst(autoUpdatePropertySource);
        return autoUpdatePropertySource;
    }

```

### 配置更新

