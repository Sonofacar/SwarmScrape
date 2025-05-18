# proxy_server.py
#
# Copyright (C) 2025 Carson Buttars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
from bs4 import BeautifulSoup
from pathlib import Path
import asyncio
import hashlib
from aiohttp import web
from nodriver import start
from cachetools import TTLCache

# File paths
if os.geteuid() != 0:
    try:
        CONFIG_DIR = os.path.join(os.environ["XDG_CONFIG_HOME"], "pyproxy")
    except:
        CONFIG_DIR = os.path.join(os.environ["HOME"], ".config", "pyproxy")
else:
    CONFIG_DIR = os.path.join("/etc", "pyproxy")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config")
API_KEYS_PATH = os.path.join(CONFIG_DIR, "keys")

# Remove style and scripts from html content
def remove_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    for s in soup.select('script'):
        s.extract()
    for s in soup.select('style'):
        s.extract()
    for s in soup.select('link'):
        s.extract()
    for s in soup.select('img'):
        s.extract()
    for s in soup.select('source'):
        s.extract()
    return soup.prettify()

# Parse configuration file (term=value format)
def load_config(path: Path):
    config = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config

# Load API keys file
def load_api_keys(path: Path):
    with path.open() as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Load configuration
if os.path.isdir(CONFIG_DIR):
    if os.path.isfile(CONFIG_PATH):
        conf = load_config(Path(CONFIG_PATH))
    else:
        os.open(path=CONFIG_PATH, flags=(os.O_RDONLY|os.O_CREAT|os.O_TRUNC), mode=0o644)
        conf = load_config(Path(CONFIG_PATH))
    if os.path.isfile(API_KEYS_PATH):
        VALID_API_KEYS = load_api_keys(Path(API_KEYS_PATH))
    else:
        os.open(path=API_KEYS_PATH, flags=(os.O_RDONLY|os.O_CREAT|os.O_TRUNC), mode=0o600)
        VALID_API_KEYS = load_api_keys(Path(API_KEYS_PATH))
else:
    os.mkdir(CONFIG_DIR)
    os.open(path=CONFIG_PATH, flags=(os.O_RDONLY|os.O_CREAT|os.O_TRUNC), mode=0o644)
    os.open(path=API_KEYS_PATH, flags=(os.O_RDONLY|os.O_CREAT|os.O_TRUNC), mode=0o600)
    conf = load_config(Path(CONFIG_PATH))
    VALID_API_KEYS = load_api_keys(Path(API_KEYS_PATH))

# Config values
POOL_SIZE = int(conf.get("pool_size", 8))
CACHE_TTL_SECONDS = int(conf.get("cache_ttl", 600))
CACHE_MAX_SIZE = int(conf.get("cache_max_size", 100))
CHROMIUM_PATH = conf.get("chromium_path", "/usr/bin/chromium")
PORT = int(conf.get("port", "8080"))

# Cache
cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL_SECONDS)

# Nodriver browser tab pool
class BrowserPool:
    def __init__(self, size: int):
        self.size = size
        self.tabs: asyncio.Queue = asyncio.Queue(maxsize=size)
        self.browser = None
        self.lock = asyncio.Lock()

    async def init_pool(self):
        async with self.lock:
            if self.browser is None:
                # self.browser = await start(headless=True, browser_executable_path=CHROMIUM_PATH)
                self.browser = await start(browser_executable_path=CHROMIUM_PATH, browser_args=['--headless'])
                tab = await self.browser.get("about:blank")
                await self.tabs.put(tab)
                for _ in range(self.size - 1):
                    tab = await self.browser.get("about:blank", new_tab=True)
                    await self.tabs.put(tab)

    async def acquire(self):
        return await self.tabs.get()

    async def release(self, tab):
        await self.tabs.put(tab)

    async def close(self):
        async with self.lock:
            if self.browser:
                await self.browser.stop()
                self.browser = None

pool = BrowserPool(POOL_SIZE)

def get_cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

def get_from_cache(url: str):
    key = get_cache_key(url)
    html = cache.get(key)
    if html:
        cache[key] = html  # Refresh TTL
    return html

def store_in_cache(url: str, html: str):
    cache[get_cache_key(url)] = html

async def authenticate(request: web.Request) -> bool:
    # api_key = request.headers.get("X-API-Key")
    api_key = request.query.get("key")
    return api_key in VALID_API_KEYS

async def handle(request):
    if not await authenticate(request):
        print("Unauthorized request")
        return web.Response(status=401, text="Unauthorized: Invalid or missing API key.")

    # api_key = request.headers.get("X-API-Key")
    api_key = request.query.get("key")
    url = request.query.get("url")
    if not url:
        return web.Response(text="Missing 'url' query parameter", status=400)

    cached = get_from_cache(url)
    if cached:
        print(api_key + " cache " + url)
        return web.Response(text=cached, content_type="text/html")

    tab = await pool.acquire()
    try:
        await tab.get(url)
        # await tab.wait_for_load()
        html = remove_tags(await tab.get_content())
        store_in_cache(url, html)
        print(api_key + " request " + url)
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Error loading page: {e}", status=500)
    finally:
        await pool.release(tab)

async def on_startup(app):
    await pool.init_pool()

async def on_cleanup(app):
    await pool.close()

app = web.Application()
app.router.add_get("/", handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

def run_proxy():
    return web.run_app(app, port=PORT)

if __name__ == "__main__":
    run_proxy(app)

