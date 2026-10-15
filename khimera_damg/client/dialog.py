import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import ParamSpec, TypeVar

_dialog_pool_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kdamg_dialog")

P = ParamSpec("P")
R = TypeVar("R")


async def run(func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    loop = asyncio.get_running_loop()
    partial_func = partial(func, *args, **kwargs)
    return await loop.run_in_executor(_dialog_pool_executor, partial_func)
