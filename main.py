from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *
import asyncio
import datetime
import aiohttp

# 定义全局变量来存储用户自定义时间和消息发送目标
user_custom_time = None
user_custom_loop = None
message_target = None  # 用于存储消息发送目标


@register("moyuren", "quirrel", "一个简单的摸鱼人日历插件", "1.2.1",
          "https://github.com/Quirrel-zh/astrbot_plugin_moyuren")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        asyncio.get_event_loop().create_task(self.scheduled_task())

    @filter.command("set_time")
    async def set_time(self, event: AstrMessageEvent, time: str, loop: int = 1):
        '''设置发送摸鱼图片的时间 格式为 HH:MM或HHMM 后面可跟检测间隔（单位分钟，默认为1，不建议太久可能会导致跳过）'''
        global user_custom_time, user_custom_loop, message_target
        time = time.strip()
        try:
            # 尝试处理 HH:MM 格式
            hour, minute = map(int, time.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
                return
            # 统一存储为 HH:MM 格式
            user_custom_time = f"{hour:02d}:{minute:02d}"
            user_custom_loop = loop
            # 保存消息发送目标
            message_target = event.unified_msg_origin
            yield event.plain_result(f"自定义时间已设置为: {user_custom_time}，每{loop}分钟检测一次")
        except ValueError:
            try:
                '''如果用户输入的时间格式为 HHMM'''
                if len(time) == 4:
                    hour = int(time[:2])
                    minute = int(time[2:])
                    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                        yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
                        return
                    # 统一存储为 HH:MM 格式
                    user_custom_time = f"{hour:02d}:{minute:02d}"
                    user_custom_loop = loop
                    # 保存消息发送目标
                    message_target = event.unified_msg_origin
                    yield event.plain_result(f"自定义时间已设置为: {user_custom_time}，每{loop}分钟检测一次")
                else:
                    yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
            except ValueError:
                yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")

    @filter.command("reset_time")
    async def reset_time(self, event: AstrMessageEvent):
        '''重置发送摸鱼图片的时间'''
        global user_custom_time, message_target
        user_custom_time = None
        message_target = None
        yield event.plain_result("自定义时间已重置")

    @filter.command("execute_now")
    async def execute_now(self, event: AstrMessageEvent):
        '''立即发送！'''

        async def get_moyu_image():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://api.52vmy.cn/api/wl/moyu') as res:
                        if res.status != 200:
                            logger.error(f"API请求失败: {res.status}")
                            return None
                        return res.url
            except Exception as e:
                logger.error(f"获取摸鱼图片时出错: {str(e)}")
                return None

        image_url = await get_moyu_image()
        if not image_url:
            yield event.plain_result("获取摸鱼图片失败，请稍后再试")
            return

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        chain = [
            Plain("📅 摸鱼人日历\n"),
            Plain("━━━━━━━━━━\n"),
            Plain(f"🎯 {current_time}\n"),
            Plain("━━━━━━━━━━\n"),
            Image(file=image_url),
            Plain("\n⏰ 摸鱼提醒：工作再累，一定不要忘记摸鱼哦 ~")
        ]
        yield event.chain_result(chain)

    async def scheduled_task(self):
        async def get_moyu_image():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://api.52vmy.cn/api/wl/moyu') as res:
                        if res.status != 200:
                            logger.error(f"API请求失败: {res.status}")
                            return None
                        return res.url
            except Exception as e:
                logger.error(f"获取摸鱼图片时出错: {str(e)}")
                return None

        while True:
            try:
                # 如果没有设置时间或目标，就跳过
                if not user_custom_time or not message_target:
                    await asyncio.sleep(60)
                    continue

                now = datetime.datetime.now()
                target_hour, target_minute = map(int, user_custom_time.split(':'))

                if now.hour == target_hour and now.minute == target_minute:
                    image_url = await get_moyu_image()
                    if image_url:
                        current_time = now.strftime("%Y-%m-%d %H:%M")
                        chain = MessageChain()
                        chain.chain.extend([
                            Plain("📅 摸鱼人日历\n"),
                            Plain("━━━━━━━━━━\n"),
                            Plain(f"🎯 {current_time}\n"),
                            Plain("━━━━━━━━━━\n"),
                            Image(file=image_url),
                            Plain("\n⏰ 摸鱼提醒：工作再累，一定不要忘记摸鱼哦 ~")
                        ])
                        try:
                            await self.context.send_message(message_target, chain)
                        except Exception as e:
                            logger.error(f"发送消息失败：{str(e)}")
                        # 等待一分钟，避免在同一分钟内重复发送
                        await asyncio.sleep(60)
                    else:
                        logger.error("获取图片失败，跳过本次发送")

                sleep_time = user_custom_loop * 60 if user_custom_loop else 60
                await asyncio.sleep(sleep_time)
            except Exception as e:
                logger.error(f"定时任务出错: {str(e)}")
                logger.error(f"错误详情: {e.__class__.__name__}")
                import traceback
                logger.error(f"堆栈信息: {traceback.format_exc()}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试

