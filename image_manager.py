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
        self.default_template = config.get(
            "default_template",
            {"name": "默认样式", "format": "摸鱼人日历\n当前时间：{time}"},
        )
        self.api_endpoints = config.get(
            "api_endpoints",
            [
                "https://api.vvhan.com/api/moyu?type=json",
                "https://api.52vmy.cn/api/wl/moyu",
            ],
        )
        self.request_timeout = config.get("request_timeout", 5)
        self.current_template_index = 0  # 添加模板索引计数器

        # 确保模板列表不为空
        if not self.templates:
            self.templates = [self.default_template]

        logger.info(f"已加载API端点: {len(self.api_endpoints)}个")
        logger.info(f"已加载消息模板: {len(self.templates)}个")

    def _get_next_template(self) -> Dict:
        """按顺序获取下一个消息模板"""
        if not self.templates:
            logger.warning("模板列表为空，使用默认模板")
            return self.default_template

        # 确保模板列表是有效的
        valid_templates = []
        for tmpl in self.templates:
            # 解析字符串模板
            if isinstance(tmpl, str):
                try:
                    tmpl_dict = json.loads(tmpl)
                    valid_templates.append(tmpl_dict)
                except json.JSONDecodeError:
                    logger.error(f"无法解析模板字符串: {tmpl}")
                    continue
            # 验证字典模板
            elif isinstance(tmpl, dict) and "format" in tmpl:
                valid_templates.append(tmpl)
            else:
                logger.warning(f"无效的模板格式: {tmpl}")

        if not valid_templates:
            logger.warning("没有有效的模板，使用默认模板")
            return self.default_template

        # 按顺序获取模板
        template = valid_templates[self.current_template_index]
        # 更新索引，实现循环
        self.current_template_index = (self.current_template_index + 1) % len(valid_templates)

        return template

    @image_operation_handler
    async def get_moyu_image(self) -> Optional[str]:
        """获取摸鱼人日历图片"""
        api_endpoints = list(self.api_endpoints)

        # 所有API都直接返回图片，逐个尝试直到成功
        for idx, api_url in enumerate(api_endpoints):
            try:
                # 设置配置中指定的超时时间
                timeout = aiohttp.ClientTimeout(total=self.request_timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # 直接下载图片
                    try:
                        img_path = await self._download_image(session, api_url)
                        if img_path:
                            logger.info(f"成功获取图片，API索引: {idx+1}")
                            return img_path
                        else:
                            logger.error(f"API {api_url} 无法获取有效图片")
                    except Exception as e:
                        logger.error(f"下载 {api_url} 失败: {str(e)}")

            except asyncio.TimeoutError:
                logger.error(f"API {api_url} 请求超时")
                continue
            except Exception as e:
                logger.error(f"处理API {api_url} 时出错: {str(e)}")
                continue

        # 所有API都失败了，尝试使用本地备用图片
        logger.error("所有API都失败了，尝试使用本地备用图片")
        local_backup = os.path.join(os.path.dirname(__file__), "backup_moyu.jpg")
        if os.path.exists(local_backup):
            # 复制备用图片到临时目录
            temp_path = os.path.join(
                self.temp_dir, f"moyu_backup_{random.randint(1000, 9999)}.jpg"
            )
            try:
                import shutil

                shutil.copy(local_backup, temp_path)
                logger.info(f"使用本地备用图片")
                return temp_path
            except Exception as e:
                logger.error(f"复制本地备用图片失败: {str(e)}")

        return None

    async def _download_image(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[str]:
        """下载图片并保存到临时文件"""
        try:
            # 使用配置中指定的超时时间
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "image/jpeg,image/png,image/webp,image/*,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }

            async with session.get(url, timeout=timeout, headers=headers) as response:
                # 检查状态码
                if response.status != 200:
                    logger.error(f"下载图片失败，状态码: {response.status}")
                    return None

                # 检查内容类型
                content_type = response.headers.get("content-type", "")

                # 读取响应内容
                content = await response.read()
                content_size = len(content)

                if not content or content_size < 1000:  # 图片通常大于1KB
                    logger.error(
                        f"下载的内容太小，可能不是有效图片: {content_size} 字节"
                    )
                    return None

                # 尝试检测图片格式
                image_format = "jpg"  # 默认格式
                if content_type:
                    if "png" in content_type:
                        image_format = "png"
                    elif "webp" in content_type:
                        image_format = "webp"
                    elif "gif" in content_type:
                        image_format = "gif"

                # 生成临时文件路径
                image_path = os.path.join(
                    self.temp_dir, f"moyu_{random.randint(1000, 9999)}.{image_format}"
                )

                # 保存图片
                with open(image_path, "wb") as f:
                    f.write(content)

                return image_path

        except asyncio.TimeoutError:
            logger.error(f"下载图片超时: {url}")
            return None
        except Exception as e:
            logger.error(f"下载图片时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return None
