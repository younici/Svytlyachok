import aiohttp
import asyncio

from bs4 import BeautifulSoup

def queue_to_index(n: int) -> int:
    x = n // 10
    y = n % 10
    return (x - 1) * 2 + y

def bias_from_index(idx: int) -> int:
    return 2 if idx % 2 == 0 else 3

async def get_status(queue, bias):
    SITE_URL = "https://www.ztoe.com.ua/unhooking-search.php"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    timeout = aiohttp.ClientTimeout(total=30)

    html = ""

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(SITE_URL, headers=headers) as resp:
                resp.raise_for_status()
                html = await resp.text()
    except asyncio.TimeoutError:
        return None
    except aiohttp.ClientError:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find_all("table")[3].select("tr")

    cells = table[1 + queue].select("td")[bias:]
    return "".join(str(td) for td in cells)