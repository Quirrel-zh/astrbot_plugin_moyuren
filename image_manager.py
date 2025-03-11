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
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.template_file = os.path.join(os.path.dirname(__file__), "templates.json")
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict:
        """加载消息模板"""
        try:
            if os.path.exists(self.template_file):
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"模板文件 {self.template_file} 不存在，将使用默认模板")
                return {
                    "templates": [],
                    "default_template": {
                        "name": "默认样式",
                        "format": "摸鱼人日历\n当前时间：{time}"
                    }
                }
        except Exception as e:
            logger.error(f"加载模板文件失败: {str(e)}")
            return {
                "templates": [],
                "default_template": {
                    "name": "默认样式",
                    "format": "摸鱼人日历\n当前时间：{time}"
                }
            }

    def _get_random_template(self) -> Dict:
        """随机获取一个消息模板"""
        templates = self.templates.get("templates", [])
        if not templates:
            return self.templates.get("default_template", {
                "name": "默认样式",
                "format": "摸鱼人日历\n当前时间：{time}"
            })
        return random.choice(templates)

    @image_operation_handler
    async def get_moyu_image(self) -> Optional[str]:
        """获取摸鱼人日历图片"""
        # 定义API端点
        api_endpoints = [
            "https://api.vvhan.com/api/moyu?type=json",
            "https://api.52vmy.cn/api/wl/moyu"
        ]
        
        for api_url in api_endpoints:
            try:
                # 设置较短的超时时间
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    if "vvhan.com" in api_url:
                        # 处理 vvhan.com API
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

    def create_moyu_message(self, image_path: str, current_time: str) -> dict:
        """创建摸鱼人日历消息"""
        try:
            # 获取随机模板
            template = self._get_random_template()
            
            # 格式化文本
            formatted_text = template['format'].format(time=current_time)
            
            # 返回文本和图片路径
            return {
                "text": formatted_text,
                "image_path": image_path
            }
        except Exception as e:
            logger.error(f"创建摸鱼人日历消息失败: {str(e)}")
            logger.error(traceback.format_exc())
            # 发生错误时使用默认格式
            return {
                "text": f"摸鱼人日历\n当前时间：{current_time}",
                "image_path": image_path
            } 