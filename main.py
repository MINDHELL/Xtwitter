import logging
from health_check import start_health_check
import os
import asyncio
import re
import requests
from tqdm import tqdm
from pyrogram import Client, filters
from playwright.async_api import async_playwright

# ========================
# CONFIG
# ========================
API_ID = 27083483
API_HASH = "1ba790464745c13ce149649d73137e52"
BOT_TOKEN = "7472633060:AAFChNfkMNsoqeExm0xKK2T5CpaGQpI9Sn0"
CHANNEL_ID = -1002800389370

bot = Client("twitter_leech_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ========================
# HELPERS
# ========================
async def download_file(url, filename):
    """Download file with progress bar"""
    r = requests.get(url, stream=True)
    total_size = int(r.headers.get("content-length", 0))
    block_size = 1024
    with open(filename, "wb") as f, tqdm(
        total=total_size, unit="B", unit_scale=True, desc=filename
    ) as pbar:
        for data in r.iter_content(block_size):
            f.write(data)
            pbar.update(len(data))
    return filename


async def scrape_tweets(username, limit=10):
    """Scrape tweets with Playwright"""
    media_items = []
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page()
        url = f"https://x.com/{username}"
        await page.goto(url)

        # Scroll to load tweets
        for _ in range(5):  # adjust scroll depth
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(2)

        # Extract tweet blocks
        tweets = await page.query_selector_all("article")
        for tweet in tweets[:limit]:
            caption = await tweet.inner_text()

            # Images
            images = await tweet.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and "profile_images" not in src:  # filter avatars
                    media_items.append(("photo", src, caption))

            # Videos (Twitter uses .mp4 in source tags)
            videos = await tweet.query_selector_all("video source")
            for vid in videos:
                src = await vid.get_attribute("src")
                if src and src.endswith(".mp4"):
                    media_items.append(("video", src, caption))

        await browser.close()

    return media_items


async def send_media_to_channel(client, items):
    """Send media to Telegram channel"""
    for idx, (mtype, url, caption) in enumerate(items, start=1):
        filename = f"{mtype}_{idx}.{'jpg' if mtype=='photo' else 'mp4'}"
        await download_file(url, filename)

        if mtype == "photo":
            await client.send_photo(CHANNEL_ID, photo=filename, caption=caption)
        else:
            await client.send_video(CHANNEL_ID, video=filename, caption=caption)

        os.remove(filename)


# ========================
# BOT COMMANDS
# ========================
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text("🤖 Playwright Twitter Leech Bot Started!\n\nUse /leech <username>")


@bot.on_message(filters.command("leech"))
async def leech(client, message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: `/leech username`", quote=True)
        return

    username = message.command[1]
    await message.reply_text(f"🔎 Scraping tweets from @{username}...")

    try:
        items = await scrape_tweets(username, limit=20)  # adjust limit
        if not items:
            await message.reply_text("⚠️ No media found.")
            return

        await send_media_to_channel(client, items)
        await message.reply_text("✅ Done! All media sent to channel.")

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# ========================
# RUN
# ========================
print("🤖 Playwright Twitter Leech Bot Started!")
bot.run()
