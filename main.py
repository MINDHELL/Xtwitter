import logging
from health_check import start_health_check
import asyncio
import os
import subprocess
from pyrogram import Client, filters
from playwright.async_api import async_playwright

# ================== CONFIG ==================
API_ID = 27083483
API_HASH = "1ba790464745c13ce149649d73137e52"
BOT_TOKEN = "7472633060:AAFChNfkMNsoqeExm0xKK2T5CpaGQpI9Sn0"
CHANNEL_ID = -1002800389370
# ============================================

bot = Client("twitter_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def install_chromium():
    """Install Chromium if not found."""
    try:
        from playwright.__main__ import main as pw_main
        print("Installing Chromium for Playwright...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("Chromium installed successfully.")
    except Exception as e:
        print("Error installing Chromium:", e)


async def fetch_twitter_media(username: str, limit=5):
    """Scrape Twitter page using Playwright and get media URLs."""
    media_list = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = f"https://twitter.com/{username}"
        await page.goto(url)
        await page.wait_for_timeout(5000)  # wait 5 seconds for tweets to load

        tweets = await page.query_selector_all("article")
        count = 0
        for tweet in tweets:
            if count >= limit:
                break
            imgs = await tweet.query_selector_all("img[src*='twimg']")
            videos = await tweet.query_selector_all("video")
            media_urls = []
            for img in imgs:
                src = await img.get_attribute("src")
                if src:
                    media_urls.append(src)
            for vid in videos:
                src = await vid.get_attribute("src")
                if src:
                    media_urls.append(src)
            if media_urls:
                media_list.append({"urls": media_urls})
                count += 1

        await browser.close()
    return media_list


@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "🤖 Twitter Leech Bot Ready!\n"
        "Use `/leech username [limit]` to fetch media."
    )


@bot.on_message(filters.command("leech"))
async def leech(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.reply_text("Usage: `/leech username [limit]`")
        username = parts[1].replace("@", "")
        limit = int(parts[2]) if len(parts) > 2 else 5
        status = await message.reply_text(f"📡 Fetching {limit} tweets from @{username}...")

        media_list = await fetch_twitter_media(username, limit)

        if not media_list:
            return await status.edit_text("❌ No media found.")

        total = len(media_list)
        for i, tweet in enumerate(media_list, start=1):
            await status.edit_text(f"⬇️ Downloading tweet {i}/{total}...")
            for url in tweet["urls"]:
                try:
                    if url.endswith(".mp4"):
                        await bot.send_video(CHANNEL_ID, url)
                    else:
                        await bot.send_photo(CHANNEL_ID, url)
                except Exception as e:
                    print("Send error:", e)

        await status.edit_text("✅ Done!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@bot.on_message(filters.regex(r"https?://(www\.)?twitter\.com/\S+"))
async def direct_link(client, message):
    try:
        url = message.matches[0].group(0)
        status = await message.reply_text("⬇️ Fetching media...")
        username = url.split("/")[3]  # extract username from link
        media_list = await fetch_twitter_media(username, limit=5)

        if not media_list:
            return await status.edit_text("❌ No media found.")

        total = len(media_list)
        for i, tweet in enumerate(media_list, start=1):
            await status.edit_text(f"⬇️ Downloading tweet {i}/{total}...")
            for url in tweet["urls"]:
                try:
                    if url.endswith(".mp4"):
                        await bot.send_video(CHANNEL_ID, url)
                    else:
                        await bot.send_photo(CHANNEL_ID, url)
                except Exception as e:
                    print("Send error:", e)

        await status.edit_text("✅ Media sent!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


# ----------------- RUN BOT -----------------
async def main():
    await install_chromium()  # self-install Chromium
    bot.run()


asyncio.run(main())
