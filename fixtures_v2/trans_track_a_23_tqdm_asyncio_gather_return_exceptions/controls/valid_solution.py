import asyncio
from tqdm.asyncio import tqdm_asyncio

def run_gather_tasks(tasks):
    return asyncio.run(tqdm_asyncio.gather(*tasks, return_exceptions=True))
