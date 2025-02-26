from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *
import asyncio
import datetime
import aiohttp

# 定义一个全局变量来存储用户自定义时间
user_custom_time = None
user_custom_loop = None

@register("helloworld", "Your Name", "一个简单的 Hello World 插件", "1.0.0", "repo url")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        asyncio.get_event_loop().create_task(self.scheduled_task())
    

    @filter.command("set_time")
    async def set_time(self, event: AstrMessageEvent, time: str, loop: int):
        '''设置发送摸鱼图片的时间 格式为 HH:MM'''
        global user_custom_time, user_custom_loop
        time = time.strip()
        try:
            hour, minute = map(int, time.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
                return
            user_custom_time = time
            user_custom_loop = loop
            yield event.plain_result(f"自定义时间已设置为: {time}，每{loop}分钟检测一次")
        except ValueError:
            try: 
                '''如果用户输入的时间格式为 HHMM'''
                if len(time) == 4:
                    hour = int(time[:2])
                    minute = int(time[2:])
                    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                        yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
                        return
                    user_custom_time = time
                    yield event.plain_result(f"自定义时间已设置为: {time}")
            except ValueError:
                yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
    @filter.command("reset_time")
    async def reset_time(self, event: AstrMessageEvent):
        '''重置发送摸鱼图片的时间'''
        global user_custom_time
        user_custom_time = None
        yield event.plain_result("自定义时间已重置")

    @filter.command("execute_now")
    async def execute_now(self, event: AstrMessageEvent):
        '''立即发送一条包含文字和图片的消息'''
        async def send_image():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.vvhan.com/api/moyu?type=json') as res:
                    if res.status != 200:
                        logger.error(f"API请求失败: {res.status}")
                        return {'url': '', 'time': '未知时间', 'title': '获取失败'}
                    try:
                        data = await res.json()
                        logger.info(f"API响应: {data}")
                        if not data.get('success'):
                            return {'url': '', 'time': '未知时间', 'title': '获取失败'}
                        return {
                            'url': data.get('url', ''),
                            'time': data.get('time', ''),
                            'title': data.get('title', '摸鱼提醒')
                        }
                    except Exception as e:
                        logger.error(f"处理API响应时出错: {str(e)}")
                        return {'url': '', 'time': '未知时间', 'title': '处理失败'}
        
        image_data = await send_image()
        if not image_data['url']:
            yield event.plain_result("获取摸鱼图片失败，请稍后再试")
            return
            
        chain = [
            Plain(f"摸鱼时间到了，{image_data['title']}！"),
            Image(file=image_data['url']),
        ]
        yield event.chain_result(chain)

    async def scheduled_task(self):
        async def send_image():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.vvhan.com/api/moyu?type=json') as res:
                    if res.status != 200:
                        logger.error(f"API请求失败: {res.status}")
                        return {'url': '', 'time': '未知时间', 'title': '获取失败'}
                    try:
                        data = await res.json()
                        logger.info(f"API响应: {data}")
                        if not data.get('success'):
                            return {'url': '', 'time': '未知时间', 'title': '获取失败'}
                        return {
                            'url': data.get('url', ''),
                            'time': data.get('time', ''),
                            'title': data.get('title', '摸鱼提醒')
                        }
                    except Exception as e:
                        logger.error(f"处理API响应时出错: {str(e)}")
                        return {'url': '', 'time': '未知时间', 'title': '处理失败'}
                    
        while True:
            try:
                now = datetime.datetime.now()
                target_time = user_custom_time or '09:00'
                target_hour, target_minute = map(int, target_time.split(':'))
                if now.hour == target_hour and now.minute == target_minute:
                    image_data = await send_image()
                    if image_data['url']:
                        chain = [
                            Plain(f"摸鱼时间到了，{image_data['title']}！"),
                            Image(file=image_data['url']),
                        ]
                        await self.context.send_message(chain)
                await asyncio.sleep(user_custom_loop * 60 if user_custom_loop else 60)  # 默认1分钟检查一次
            except Exception as e:
                logger.error(f"定时任务出错: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试

