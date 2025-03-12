import aiohttp
import random
from datetime import datetime
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image
import traceback
import os
import asyncio
from typing import List, Optional, Union, Dict
from functools import wraps
from astrbot.api.event import MessageChain
import json

def image_operation_handler(func):
    """图片操作错误处理装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except aiohttp.ClientError as e:
            logger.error(f"网络请求错误: {str(e)}")
        except asyncio.TimeoutError:
            logger.error("请求超时")
        except Exception as e:
            logger.error(f"{func.__name__} 执行出错: {str(e)}")
            logger.error(traceback.format_exc())
        return None
    return wrapper

class ImageManager:
    def __init__(self, temp_dir: str, config: Dict):
        """初始化图片管理器
        
        Args:
            temp_dir: 临时目录路径
            config: 从_conf_schema.json加载的配置
        """
        self.temp_dir = temp_dir
        self.config = config
        self.templates = config.get("templates", [])
        self.default_template = config.get("default_template", {
            "name": "默认样式",
            "format": "摸鱼人日历\n当前时间：{time}"
        })
        self.api_endpoints = config.get("api_endpoints", [
            "https://api.vvhan.com/api/moyu?type=json",
            "https://api.52vmy.cn/api/wl/moyu"
        ])
        self.request_timeout = config.get("request_timeout", 5)
        
        logger.info(f"已加载API端点: {len(self.api_endpoints)}个")
        logger.info(f"已加载消息模板: {len(self.templates)}个")
        
    def _get_random_template(self) -> Dict:
        """获取随机消息模板"""
        if not self.templates:
            return self.default_template
        return random.choice(self.templates)

    @image_operation_handler
    async def get_moyu_image(self) -> Optional[str]:
        """获取摸鱼人日历图片"""
        for api_url in self.api_endpoints:
            try:
                # 设置配置中指定的超时时间
                timeout = aiohttp.ClientTimeout(total=self.request_timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if "vvhan.com" in api_url or ("?type=json" in api_url or ".json" in api_url):
                        # 处理返回JSON的API
                        try:
                            async with session.get(api_url) as response:
                                if response.status == 200:
                                    try:
                                        data = await response.json()
                                        if 'url' in data:
                                            image_url = data['url']
                                            return await self._download_image(session, image_url)
                                    except json.JSONDecodeError:
                                        logger.error(f"{api_url} 返回的不是有效的JSON")
                        except Exception as e:
                            logger.error(f"{api_url} 请求失败: {str(e)}")
                    
                    else:
                        # 直接下载图片的API
                        try:
                            return await self._download_image(session, api_url)
                        except Exception as e:
                            logger.error(f"直接下载 {api_url} 失败: {str(e)}")
                        
            except asyncio.TimeoutError:
                logger.error(f"API {api_url} 请求超时")
                continue
            except Exception as e:
                logger.error(f"API {api_url} 获取失败: {str(e)}")
                continue
                
        # 所有API都失败了，尝试使用本地备用图片
        logger.error("所有API都失败了，尝试使用本地备用图片")
        local_backup = os.path.join(os.path.dirname(__file__), "backup_moyu.jpg")
        if os.path.exists(local_backup):
            # 复制备用图片到临时目录
            temp_path = os.path.join(self.temp_dir, f"moyu_backup_{random.randint(1000, 9999)}.jpg")
            try:
                import shutil
                shutil.copy(local_backup, temp_path)
                return temp_path
            except Exception as e:
                logger.error(f"复制本地备用图片失败: {str(e)}")
        
        return None
        
    async def _download_image(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """下载图片并保存到临时文件"""
        try:
            # 使用较短的超时时间
            timeout = aiohttp.ClientTimeout(total=5)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            async with session.get(url, timeout=timeout, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"下载图片失败，状态码: {response.status}")
                    return None
                
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                
                # 有些API可能不返回正确的content-type，所以我们不严格检查
                if not (content_type.startswith('image/') or 'octet-stream' in content_type):
                    logger.warning(f"返回内容可能不是图片: {content_type}，但仍尝试保存")
                
                # 读取响应内容
                content = await response.read()
                if not content or len(content) < 1000:  # 图片通常大于1KB
                    logger.error(f"下载的内容太小，可能不是有效图片: {len(content)} 字节")
                    return None
                
                # 生成临时文件路径
                image_path = os.path.join(self.temp_dir, f"moyu_{random.randint(1000, 9999)}.jpg")
                
                # 保存图片
                with open(image_path, 'wb') as f:
                    f.write(content)
                
                return image_path
                
        except asyncio.TimeoutError:
            logger.error("下载图片超时")
            return None
        except Exception as e:
            logger.error(f"下载图片时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return None 