from astrbot.api.event import AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api import logger
from datetime import datetime, timedelta
import re
import traceback
from functools import wraps
from typing import AsyncGenerator, Optional

def command_error_handler(func):
    """命令错误处理装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> AsyncGenerator[MessageEventResult, None]:
        try:
            async for result in func(*args, **kwargs):
                yield result
        except ValueError as e:
            # 参数验证错误
            event = args[1] if len(args) > 1 else None
            if event and isinstance(event, AstrMessageEvent):
                yield event.plain_result(f"参数错误: {str(e)}")
        except Exception as e:
            # 其他未预期的错误
            logger.error(f"{func.__name__} 执行出错: {str(e)}")
            logger.error(traceback.format_exc())
            event = args[1] if len(args) > 1 else None
            if event and isinstance(event, AstrMessageEvent):
                yield event.plain_result("操作执行失败，请查看日志获取详细信息")
    return wrapper

class CommandHelper:
    def __init__(self, config_manager, image_manager, context, scheduler=None):
        self.config_manager = config_manager
        self.image_manager = image_manager
        self.context = context
        self.scheduler = scheduler  # 添加调度器引用
        
    def parse_time_format(self, time_str: str) -> tuple[int, int]:
        """解析时间格式，支持HH:MM和HHMM格式"""
        time_str = time_str.strip()
        
        # 使用正则表达式匹配时间格式
        colon_pattern = re.compile(r'^(\d{1,2}):(\d{1,2})$')
        no_colon_pattern = re.compile(r'^(\d{4})$')
        
        # 尝试匹配 HH:MM 格式
        match = colon_pattern.match(time_str)
        if match:
            hour, minute = map(int, match.groups())
        else:
            # 尝试匹配 HHMM 格式
            match = no_colon_pattern.match(time_str)
            if not match:
                raise ValueError("时间格式不正确，请使用 HH:MM 或 HHMM 格式")
            time_digits = match.group(1)
            hour = int(time_digits[:2])
            minute = int(time_digits[2:])
        
        # 验证时间范围
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("时间范围不正确，小时应在0-23之间，分钟应在0-59之间")
            
        return hour, minute

    def normalize_session_id(self, event: AstrMessageEvent) -> str:
        """标准化会话ID，确保格式一致"""
        try:
            target = event.unified_msg_origin
            return target
        except Exception as e:
            logger.error(f"标准化会话ID时出错: {str(e)}")
            return event.unified_msg_origin  # 返回原始ID作为后备

    @command_error_handler
    async def handle_set_time(self, event: AstrMessageEvent, time_str: str) -> AsyncGenerator[MessageEventResult, None]:
        """处理设置时间命令"""
        try:
            # 格式化时间字符串
            if len(time_str) == 4:  # HHMM格式
                time_str = f"{time_str[:2]}:{time_str[2:]}"
            elif len(time_str) != 5:  # 不是HH:MM格式
                yield event.make_result().message("时间格式错误，请使用HH:MM或HHMM格式")
                return

            # 验证时间格式
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour < 24 and 0 <= minute < 60):
                    yield event.make_result().message("时间格式错误，小时必须在0-23之间，分钟必须在0-59之间")
                    return
            except ValueError:
                yield event.make_result().message("时间格式错误，请使用HH:MM或HHMM格式")
                return

            # 获取标准化的群组ID
            target = self.normalize_session_id(event)
            
            # 更新配置
            if target not in self.config_manager.group_settings:
                self.config_manager.group_settings[target] = {}
            self.config_manager.group_settings[target]['custom_time'] = time_str
            
            # 保存配置
            self.config_manager.save_config()
            
            # 计算等待时间
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 如果目标时间已经过去，则设置为明天的这个时间
            if target_time <= now:
                target_time += timedelta(days=1)
            
            # 计算等待的秒数
            wait_seconds = int((target_time - now).total_seconds())
            hours = wait_seconds // 3600
            minutes = (wait_seconds % 3600) // 60
            seconds = wait_seconds % 60
            
            # 格式化等待时间显示
            wait_time_str = ""
            if hours > 0:
                wait_time_str += f"{hours}小时"
            if minutes > 0:
                wait_time_str += f"{minutes}分钟"
            if seconds > 0 or not wait_time_str:
                wait_time_str += f"{seconds}秒"
            
            # 唤醒调度器并更新任务队列
            if hasattr(self, 'scheduler') and self.scheduler:
                self.scheduler.update_task_queue()
                self.scheduler.wakeup_event.set()
            
            # 使用 make_result() 构建消息
            result = event.make_result()
            result.message(f"✅ 定时发送已设置\n时间：{time_str}\n下一次发送将在 {wait_time_str}后进行")
            yield result
            
        except Exception as e:
            logger.error(f"设置时间时出错: {str(e)}")
            logger.error(traceback.format_exc())
            yield event.make_result().message("❌ 设置时间时出错，请查看日志")

    @command_error_handler
    async def handle_reset_time(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """取消定时发送摸鱼图片的设置"""
        target = self.normalize_session_id(event)
        if target not in self.config_manager.group_settings:
            yield event.make_result().message("❌ 当前群聊未设置自定义时间")
            return

        # 检查是否有自定义时间设置
        if 'custom_time' not in self.config_manager.group_settings[target]:
            yield event.make_result().message("❌ 当前群聊未设置自定义时间")
            return

        # 获取当前时间设置，用于显示
        current_time = self.config_manager.group_settings[target]['custom_time']
        
        # 保留触发词设置
        trigger_word = self.config_manager.group_settings[target].get('trigger_word', '摸鱼')
        
        # 重置时间设置
        if 'custom_time' in self.config_manager.group_settings[target]:
            del self.config_manager.group_settings[target]['custom_time']
            
        # 如果没有其他设置，则保持触发词
        if len(self.config_manager.group_settings[target]) == 0:
            self.config_manager.group_settings[target] = {'trigger_word': trigger_word}
            
        self.config_manager.save_config()
        
        # 更新调度器
        if hasattr(self, 'scheduler') and self.scheduler:
            # 从任务队列中删除对应任务
            self.scheduler.remove_task(target)
            # 更新任务队列
            self.scheduler.update_task_queue()
            # 唤醒调度器
            self.scheduler.wakeup_event.set()
            
        yield event.make_result().message(f"✅ 已取消定时发送\n原定时间：{current_time}\n触发词仍可正常使用")

    @command_error_handler
    async def handle_list_time(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """列出当前群聊的时间设置"""
        target = self.normalize_session_id(event)
        if target not in self.config_manager.group_settings:
            yield event.make_result().message("当前群聊未设置任何配置")
            return

        settings = self.config_manager.group_settings[target]
        trigger_word = settings.get('trigger_word', '摸鱼')
        time_setting = settings.get('custom_time', '未设置')
        yield event.make_result().message(f"当前群聊设置:\n发送时间: {time_setting}\n触发词: {trigger_word}")

    @command_error_handler
    async def handle_set_trigger(self, event: AstrMessageEvent, trigger: str) -> AsyncGenerator[MessageEventResult, None]:
        """设置触发词，默认为"摸鱼" """
        if not trigger or len(trigger.strip()) == 0:
            raise ValueError("触发词不能为空")
            
        target = self.normalize_session_id(event)
        trigger = trigger.strip()
        
        if target not in self.config_manager.group_settings:
            self.config_manager.group_settings[target] = {'trigger_word': trigger}
        else:
            self.config_manager.group_settings[target]['trigger_word'] = trigger
            
        self.config_manager.save_config()
        yield event.make_result().message(f"✅ 已设置触发词为: {trigger}")

    @command_error_handler
    async def handle_execute_now(self, event: AstrMessageEvent) -> AsyncGenerator[MessageEventResult, None]:
        """立即发送摸鱼人日历"""
        try:
            image_path = await self.image_manager.get_moyu_image()
            if not image_path:
                yield event.make_result().message("获取摸鱼图片失败，请稍后再试")
                return

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 获取消息内容
            template = self.image_manager._get_random_template()
            text = template["format"].format(time=current_time)
            
            logger.info(f"使用模板: {template['name']}")
            
            # 创建简单的消息段列表传递给chain_result
            from astrbot.api.message_components import Plain, Image
            message_segments = [
                Plain(text),
                Image(file=image_path)
            ]
            
            # 使用消息段列表
            yield event.chain_result(message_segments)
            
        except Exception as e:
            logger.error(f"执行立即发送命令时出错: {str(e)}")
            logger.error(traceback.format_exc())
            yield event.make_result().message("发送摸鱼人日历失败，请查看日志获取详细信息")

    async def handle_message(self, event: AstrMessageEvent) -> None:
        """处理消息事件，检测触发词"""
        # 获取消息内容和来源
        message_text = event.message_obj.message_str
        target = self.normalize_session_id(event)
        
        # 如果是命令消息或群未配置，则跳过处理
        if message_text.startswith('/') or target not in self.config_manager.group_settings:
            return
        
        # 获取触发词并检查
        trigger_word = self.config_manager.group_settings[target].get('trigger_word', '摸鱼')
        if trigger_word not in message_text:
            return
            
        # 获取并发送摸鱼图片
        try:
            image_path = await self.image_manager.get_moyu_image()
            if not image_path:
                return
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 获取消息内容
            template = self.image_manager._get_random_template()
            text = template["format"].format(time=current_time)
            
            # 创建消息段列表
            from astrbot.api.message_components import Plain, Image
            message_segments = [
                Plain(text),
                Image(file=image_path)
            ]
            
            # 使用send_message直接发送消息段列表
            from astrbot.api.event import MessageChain
            message_chain = MessageChain(message_segments)
            await self.context.send_message(target, message_chain)
        except Exception as e:
            logger.error(f"发送摸鱼人日历失败: {str(e)}")
            logger.error(traceback.format_exc()) 