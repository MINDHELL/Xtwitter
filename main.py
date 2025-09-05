import logging
from health_check import start_health_check
import asyncio
from pyrogram import Client, filters
from playwright.async_api import async_playwright
import os

# =====================
# 🔧 Bot Config
# =====================
API_ID = 27083483
API_HASH = "1ba790464745c13ce149649d73137e52"
BOT_TOKEN = "7472633060:AAFChNfkMNsoqeExm0xKK2T5CpaGQpI9Sn0"
CHANNEL_ID = -1002800389370  # your channel id

bot = Client("twitter_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# =====================
# 🎭 Playwright Scraper
# =====================
async def scrape_twitter(username: str, limit: int = 5):
    """Scrapes Twitter profile for media using Chromium."""
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # force Chromium
        page = await browser.new_page()
        await page.goto(f"https://twitter.com/{username}", timeout=60000)

        # Wait for tweets to load
        await page.wait_for_selector("article", timeout=60000)

        tweets = await page.query_selector_all("article")
        count = 0

        for tweet in tweets:
            if count >= limit:
                break

            try:
                content = await tweet.inner_text()
                media = await tweet.query_selector_all("img, video")

                for m in media:
                    src = await m.get_attribute("src")
                    if src and ("twimg" in src or "video" in src):
                        results.append({"caption": content, "url": src})
                        count += 1
                        if count >= limit:
                            break
            except Exception as e:
                print("Error parsing tweet:", e)

        await browser.close()
    return results


# =====================
# 🤖 Bot Commands
# =====================
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("🤖 Twitter Leech Bot Started!\nSend `/leech username` to begin.")


@bot.on_message(filters.command("leech"))
async def leech_cmd(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("❌ Usage: `/leech username`")
            return

        username = parts[1]
        msg = await message.reply_text(f"🔎 Fetching posts from **{username}** ...")

        posts = await scrape_twitter(username, limit=10)

        if not posts:
            await msg.edit("⚠️ No media found!")
            return

        for idx, post in enumerate(posts, start=1):
            progress = f"📤 Uploading {idx}/{len(posts)}"
            await msg.edit(progress)

            try:
                if post["url"].endswith(".mp4"):
                    await bot.send_video(
                        chat_id=CHANNEL_ID,
                        video=post["url"],
                        caption=post["caption"][:200]
                    )
                else:
                    await bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=post["url"],
                        caption=post["caption"][:200]
                    )
            except Exception as e:
                print("Upload error:", e)

        await msg.edit("✅ All posts uploaded!")

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# =====================
# 🚀 Run Bot
# =====================
if __name__ == "__main__":
    bot.run()
