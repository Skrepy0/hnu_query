import re

from pydantic import BaseModel


class Dormitory(BaseModel):
    """园区/楼栋未识别时为 None；保留原始宿舍文字和房间号。"""

    park: str | None = None
    build: str | None = None
    room: str
    raw_dormitory: str

    @classmethod
    def from_parsed_value(cls, park: str, build: str, room: str) -> "Dormitory":
        """从已知园区/楼栋构造；合法取值与 Rust Dormitory 一致。"""
        return cls(park=park, build=build, room=room, raw_dormitory=park + build)

    def successfully_parsed(self) -> bool:
        return self.park is not None and self.build is not None


def parse_dormitory(dormitory: str, room: str) -> Dormitory:
    park = build = None
    # 与 Rust 一样依次判断，后面的匹配可以覆盖前面的结果。
    for keyword, candidate, pattern, group in (
        ("德智", "德智园区", r"\d+栋", 0),
        ("天马", "天马园区", r"[一二三四]区\d+栋", 0),
        ("望麓桥", "望麓桥学生公寓", r"\d+栋", 0),
        ("牛头山", "牛头山学生公寓", r"\d+栋", 0),
        ("财院校区", "财院校区", r"[南北]?(\d+|[AB])[舍栋]?", 1),
        ("南校区", "南校区", r"\d+舍", 0),
    ):
        if keyword in dormitory:
            park = candidate
            match = re.search(pattern, dormitory)
            build = match[group] if match is not None else None
    return Dormitory(park=park, build=build, room=room, raw_dormitory=dormitory)
