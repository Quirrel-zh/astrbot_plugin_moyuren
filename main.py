from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event.filter import event_message_type, EventMessageType
import os
import tempfile
import traceback

from .config_manager import ConfigManager
from .image_manager import ImageManager
from .command_handler import CommandHelper
from .scheduler import Scheduler


@register(
    "moyuren",
    "quirrel",
    "一个功能完善的摸鱼人日历插件",
    "2.3.1",
    "https://github.com/Quirrel-zh/astrbot_plugin_moyuren",
)
class MoyuRenPlugin(Star):
    """摸鱼人日历插件

    功能：
    - 在指定时间自动发送摸鱼人日历
    - 支持精确定时，无需轮询检测
    - 支持多群组不同时间设置
    - 支持自定义触发词，默认为"摸鱼"
    - 每次随机选择不同的排版样式
    - 支持自定义API端点和消息模板

    命令：
    - /set_time HH:MM - 设置发送时间，格式为24小时制
    - /reset_time - 重置当前群聊的时间设置
    - /list_time - 查看当前群聊的时间设置
    - /next_time - 查看下一次执行的时间
    - /execute_now - 立即发送摸鱼人日历
    - /set_trigger 触发词 - 设置触发词，默认为"摸鱼"
    """

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(os.path.dirname(__file__), "config.json")

        # 初始化各个管理器
        logger.info("开始初始化摸鱼人插件...")
        self.config_manager = ConfigManager(self.config_file)

        # 使用从AstrBot获取的配置（通过_conf_schema.json）
        self.plugin_config = config or {}
        logger.info(f"加载插件配置: {self.plugin_config}")

        self.image_manager = ImageManager(self.temp_dir, self.plugin_config)
        self.scheduler = Scheduler(self.config_manager, self.image_manager, context)
        self.command_helper = CommandHelper(
            self.config_manager, self.image_manager, context, self.scheduler
        )

        # 加载配置
        logger.info("加载摸鱼人插件配置...")
        self.config_manager.load_config()
        logger.info(f"当前配置: {self.config_manager.group_settings}")

        # 启动定时任务
        logger.info("启动摸鱼人插件定时任务...")
        self.scheduler.start()
        # 立即更新任务队列
        self.scheduler.update_task_queue()
        logger.info("摸鱼人插件初始化完成")

        # 保存实例引用
        MoyuRenPlugin._instance = self

    @filter.command("set_time")
    async def set_time(self, event: AstrMessageEvent, time: str):
        """设置发送摸鱼图片的时间 格式为 HH:MM或HHMM"""
        async for result in self.command_helper.handle_set_time(event, time):
            yield result

    @filter.command("reset_time")
    async def reset_time(self, event: AstrMessageEvent):
        """重置发送摸鱼图片的时间"""
        async for result in self.command_helper.handle_reset_time(event):
            yield result

    @filter.command("list_time")
    async def list_time(self, event: AstrMessageEvent):
        """列出当前群聊的时间设置"""
        async for result in self.command_helper.handle_list_time(event):
            yield result

    @filter.command("set_trigger")
    async def set_trigger(self, event: AstrMessageEvent, trigger: str):
        """设置触发词，默认为"摸鱼" """
        async for result in self.command_helper.handle_set_trigger(event, trigger):
            yield result

    @filter.command("execute_now")
    async def execute_now(self, event: AstrMessageEvent):
        """立即发送摸鱼人日历"""
        async for result in self.command_helper.handle_execute_now(event):
            yield result

    @event_message_type(EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """处理消息事件，检测触发词"""
        await self.command_helper.handle_message(event)

    async def terminate(self):
        """终止插件的所有活动"""
        try:
            # 获取实例
            instance = getattr(self, "_instance", None)
            if not instance:
                logger.error("找不到摸鱼人插件实例，无法正常终止")
                return

            # 停止定时任务
            await instance.scheduler.stop()
            logger.info("摸鱼人日历定时任务已停止")

            # 清理临时文件
            if hasattr(instance, "temp_dir") and os.path.exists(instance.temp_dir):
                for file in os.listdir(instance.temp_dir):
                    try:
                        os.remove(os.path.join(instance.temp_dir, file))
                    except Exception as e:
                        logger.error(f"删除临时文件失败: {str(e)}")
                try:
                    os.rmdir(instance.temp_dir)
                    logger.info("已清理摸鱼人插件临时文件")
                except Exception as e:
                    logger.error(f"删除临时目录失败: {str(e)}")
        except Exception as e:
            logger.error(f"终止插件时出错: {str(e)}")
            logger.error(traceback.format_exc())
