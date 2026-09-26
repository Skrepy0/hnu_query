from hnu_query.credential.file import file, preview_file
from hnu_query.credential.token import CaToken
from .models import Rank
from .parse import preview_file_name, parse_rank

UNDERGRADUATE_MAJOR_ALL_TEMPLATE_ID = "02a70e11bc89b40dc2ef6ed14851ce25"


async def get_grade_rank(ca_token: CaToken) -> Rank:
    """获取本科生可信电子凭证中的成绩排名。

    仅计算主修课，辅修课不计算在内。

    对应 Rust ``ca::grade_rank::get_grade_rank``。
    """
    json_str = await preview_file(ca_token, UNDERGRADUATE_MAJOR_ALL_TEMPLATE_ID)
    file_name = preview_file_name(json_str)
    pdf_bytes = await file(ca_token, file_name)
    return parse_rank(pdf_bytes)
