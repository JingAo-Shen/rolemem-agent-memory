import asyncio
from tqdm.asyncio import tqdm_asyncio

def run_gather_tasks(tasks):
    # Stale: gather does not support return_exceptions
    return asyncio.run(tqdm_asyncio.gather(*tasks))
