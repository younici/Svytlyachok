from bs4 import BeautifulSoup

import untils.cache as cache

import untils.tools as tools

import os

CAN_CACHE = os.getenv("CAN_CACHE") == "true"

import logging

log = logging.getLogger(__name__)

log.info(f"cache status: {CAN_CACHE}")

async def parse(queue: int):
    queue = tools.queue_to_index(queue)
    bias = tools.bias_from_index(queue)

    text = ""

    if CAN_CACHE:
        text = await cache.get_cache(queue)
        log.info("cache used")
    else:
        text = await tools.get_status(queue, bias)

    if text is None:
        return None

    status = []
    colors = []

    html = BeautifulSoup(text, "html.parser")

    for i in html:
        style = i.get("style", "")
        color = None

        for part in style.split(";"):
            part = part.strip()
            if part.startswith("background"):
                color = part.split(":", 1)[1].strip()
                break

        colors.append(color)

    for c in colors:
        if c == "#ffffff":
            status.append(0)
        else:
            status.append(1)
    return status