from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import *
import asyncio
import datetime
import aiohttp

# 定义一个全局变量来存储用户自定义时间
user_custom_time = None

@register("helloworld", "Your Name", "一个简单的 Hello World 插件", "1.0.0", "repo url")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.context.loop.create_task(scheduled_task())
    

@filter.command("set_time")
async def set_time(self, event: AstrMessageEvent, time: str):
    '''设置发送摸鱼图片的时间 格式为 HH:MM'''
    global user_custom_time
    time = time.strip()
    try:
        hour, minute = map(int, time.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            yield event.plain_result("时间格式错误，请输入正确的格式，例如：09:00或0900")
            return
        user_custom_time = time
        yield event.plain_result(f"自定义时间已设置为: {time}")
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
    image_data = await send_image()
    chain = [
        Plain(f"摸鱼时间到了，今天是{image_data['time']}！"),
        Image(file=image_data['url']),
    ]
    yield event.chain_result(chain)

async def scheduled_task(self, event: AstrMessageEvent):
    while True:
        now = datetime.datetime.now()
        target_time = user_custom_time or '09:00'
        target_hour, target_minute = map(int, target_time.split(':'))
        if now.hour == target_hour and now.minute == target_minute:
            image_data = await send_image()
            chain = [
                Plain(f"摸鱼时间到了，今天是{image_data['time']}！"),
                Image(file=f"{image_data['url']}"),
            ]
            yield event.chain_result(chain)
        await asyncio.sleep(30)  # 每30分钟检查一次

async def send_image():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.vvhan.com/api/moyu?type=json') as res:
            if not res.success:
                return res.message
            return {
                'url': res.url,
                'title': res.title,
                'time': res.time,
            }
            

