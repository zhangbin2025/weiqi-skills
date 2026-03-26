"""棋谱下载源集合"""

from .base import (
    BaseSourceFetcher,
    FetchResult,
    get_fetcher_for_url,
    get_fetcher_by_name,
    list_fetchers,
    register_fetcher,
)

# 自动导入所有源
from . import fetch_ogs
from . import fetch_fox
from . import fetch_101
from . import fetch_yike
from . import fetch_yuanluobo

__all__ = [
    'BaseSourceFetcher',
    'FetchResult',
    'get_fetcher_for_url',
    'get_fetcher_by_name',
    'list_fetchers',
    'register_fetcher',
]
