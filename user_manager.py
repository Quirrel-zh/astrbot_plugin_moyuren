from astrbot.api.event import AstrMessageEvent, MessageEventResult
from astrbot.api import logger
import json
import os


def parse_manager_id(event: AstrMessageEvent) -> str:
    sender_id = event.get_sender_id()
    platform = event.get_platform_name()
    manager_id = platform + "_" + sender_id
    return manager_id


class UserManager:
    def __init__(self, config_file: str):
        self.manager_file = config_file
        self.manager_id = ""
        self.load_manager()

    def load_manager(self):
        if os.path.exists(self.manager_file):
            try:
                with open(self.manager_file, 'r') as f:
                    data = json.load(f)
                    self.manager_id = data.get('manager_id')

            except Exception as e:
                logger.error(f"加载管理者信息失败: {e}")

    def has_manager(self) -> bool:
        return self.manager_id != ""

    def save_manager(self, event: AstrMessageEvent):
        self.manager_id = parse_manager_id(event)
        data = {
            'manager_id': self.manager_id,
        }
        try:
            with open(self.manager_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"保存管理者信息失败: {e}")

    def is_manager(self, event: AstrMessageEvent) -> bool:
        try:
            manager_id = parse_manager_id(event)
            if self.manager_id == manager_id:
                return True
            logger.info(f"check_manager not pass: {manager_id}, 已设置的为：{self.manager_id}")
            return False
        except Exception as e:
            logger.error(f"判断管理者信息失败: {e}")
            return False
