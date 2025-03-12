import json
import os
from astrbot.api import logger
import traceback
from functools import wraps
from typing import Dict, Any, Optional, Callable


def config_operation_handler(func: Callable):
    """配置操作错误处理装饰器"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except json.JSONDecodeError as je:
            logger.error(f"JSON解析错误: {str(je)}")
            if hasattr(self, "config_file") and os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.bak"
                os.rename(self.config_file, backup_file)
                logger.info(f"已将损坏的配置文件备份为: {backup_file}")
        except (IOError, OSError) as e:
            logger.error(f"文件操作错误: {str(e)}")
        except Exception as e:
            logger.error(f"{func.__name__} 执行出错: {str(e)}")
            logger.error(traceback.format_exc())
        return None

    return wrapper


class ConfigManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.group_settings: Dict[str, Dict[str, Any]] = {}

    @config_operation_handler
    def load_config(self) -> Optional[bool]:
        """加载配置文件

        Returns:
            bool: 加载是否成功
        """
        self.group_settings = {}  # 确保初始化为空字典

        if not os.path.exists(self.config_file):
            logger.info("配置文件不存在，将创建新的配置文件")
            return self.save_config()

        with open(self.config_file, "r", encoding="utf-8") as f:
            loaded_data = f.read().strip()
            if not loaded_data:  # 处理空文件的情况
                logger.warning("配置文件为空，使用默认空字典")
                return True

            loaded_settings = json.loads(loaded_data)
            if not isinstance(loaded_settings, dict):
                raise ValueError(
                    f"配置文件格式错误：期望字典类型，实际为 {type(loaded_settings)}"
                )

            # 验证加载的配置并迁移旧配置
            for target, settings in loaded_settings.items():
                if not isinstance(settings, dict):
                    logger.warning(f"跳过无效的群设置 {target}: {settings}")
                    continue

                # 初始化群设置
                self.group_settings[target] = {}

                # 兼容旧版本配置，保留custom_time
                if "custom_time" in settings:
                    self.group_settings[target]["custom_time"] = settings["custom_time"]

                # 加载触发词设置，如果不存在则使用默认值"摸鱼"
                self.group_settings[target]["trigger_word"] = settings.get(
                    "trigger_word", "摸鱼"
                )

            logger.info(f"已加载摸鱼人配置: {len(self.group_settings)}个群聊的设置")
            return True

    @config_operation_handler
    def save_config(self) -> Optional[bool]:
        """保存配置到文件

        Returns:
            bool: 保存是否成功
        """
        # 确保group_settings是字典类型
        if not isinstance(self.group_settings, dict):
            raise ValueError(
                f"保存配置失败：group_settings类型错误 ({type(self.group_settings)})"
            )

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.group_settings, f, ensure_ascii=False, indent=2)
        logger.info("摸鱼人配置已保存")
        return True
