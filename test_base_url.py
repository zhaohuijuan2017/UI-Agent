"""测试 LLM API Base URL 配置。"""

import os

# 设置 API Key
os.environ['ZHIPUAI_API_KEY'] = '34eeadd155244053894ffadb2c1999a4.vu8hn2jUQdoGzJ9O'

from src.config.config_manager import ConfigManager
from src.config.schema import APIConfig

print('=' * 60)
print('LLM API Base URL 配置测试')
print('=' * 60)

# 测试 1: 默认配置（无 base_url）
print('\n[测试 1] 默认配置（无自定义 base_url）')
config_manager = ConfigManager('config/main.yaml')
config = config_manager.load_config()
print(f'  API Key: {config.api.zhipuai_api_key[:20]}...')
print(f'  Model: {config.api.model}')
print(f'  Base URL: {config.api.base_url or "官方 API"}')

# 测试 2: 创建自定义 base_url 的配置
print('\n[测试 2] 自定义 base_url 配置')
custom_api_config = APIConfig(
    zhipuai_api_key='test-key',
    model='glm-4-flash',
    timeout=30,
    base_url='http://localhost:8080/v1'
)
print(f'  API Key: {custom_api_config.zhipuai_api_key}')
print(f'  Model: {custom_api_config.model}')
print(f'  Base URL: {custom_api_config.base_url}')

# 测试 3: ZhipuAI 客户端初始化
print('\n[测试 3] ZhipuAI 客户端初始化')
try:
    from zhipuai import ZhipuAI

    # 官方 API
    client_official = ZhipuAI(api_key=os.environ['ZHIPUAI_API_KEY'])
    print(f'  官方 API 客户端: 已创建')

    # 自定义 base_url
    client_custom = ZhipuAI(
        api_key=os.environ['ZHIPUAI_API_KEY'],
        base_url='http://localhost:8080/v1'
    )
    print(f'  自定义 base_url 客户端: 已创建')

    print('  ZhipuAI 客户端支持 base_url 参数')
except ImportError as e:
    print(f'  错误: {e}')

print('\n' + '=' * 60)
print('配置说明:')
print('=' * 60)
print('在 config/main.yaml 中配置 base_url:')
print()
print('api:')
print('  zhipuai:')
print('    api_key: your-api-key')
print('    model: glm-4v-flash')
print('    timeout: 30')
print('    # 留空使用官方 API')
print('    base_url: null')
print()
print('    # 或设置自定义代理/兼容接口')
print('    # base_url: http://localhost:8080/v1')
print('    # base_url: https://api.openai.com/v1')
print()
print('=' * 60)
