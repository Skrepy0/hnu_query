from collections.abc import Sequence

from .client import HdjwClient
from .models import DataSource, Display, Range, Rank, RankDetail
from .token import HdjwToken

__all__ = ["DataSource", "Display", "Range", "Rank", "RankDetail", "get_rank"]


async def get_rank(
    hdjw_token: HdjwToken,
    selection: Sequence[tuple[int, int]] = (),
    range: Range = Range.Major,
    data_source: DataSource = DataSource.Total,
    display: Display = Display.Max,
) -> Rank:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_rank(selection, range, data_source, display)
