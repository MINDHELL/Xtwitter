import logging
from health_check import start_health_check
import asyncio
from pyrogram import Client, filters
from playwright.async_api import async_playwright

# =====================
# 🔧 Bot Config
# =====================
API_ID = 27083483
API_HASH = "1ba790464745c13ce149649d73137e52"
BOT_TOKEN = "7472633060:AAFChNfkMNsoqeExm0xKK2T5CpaGQpI9Sn0"
CHANNEL_ID = -1002800389370

bot = Client("twitter_leech", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# =====================
# 🎭 Playwright Scraper
# =====================
async def scrape_twitter(username: str, limit: int = 20):
    """Scrape media from a Twitter profile using scrolling."""
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://twitter.com/{username}", timeout=60000)

        await page.wait_for_selector("article", timeout=60000)
        last_height = 0

        while len(results) < limit:
            tweets = await page.query_selector_all("article")

            for tweet in tweets:
                if len(results) >= limit:
                    break
                try:
                    caption = await tweet.inner_text()
                    media = await tweet.query_selector_all("img, video")

                    for m in media:
                        src = await m.get_attribute("src")
                        if src and ("twimg" in src or "video" in src):
                            # Avoid duplicates
                            if not any(r["url"] == src for r in results):
                                results.append({"caption": caption, "url": src})
                                if len(results) >= limit:
                                    break
                except Exception as e:
                    print("Parse error:", e)

            # Scroll down
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Detect if page stopped loading
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        await browser.close()
    return results


# =====================
# 🤖 Bot Commands
# =====================
@bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text("🤖 Twitter Leech Bot Ready!\nUse `/leech username [limit]`")


@bot.on_message(filters.command("leech"))
async def leech_cmd(client, message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.reply_text("❌ Usage: `/leech username [limit]`")
            return

        username = parts[1]
        limit = int(parts[2]) if len(parts) > 2 else 10

        msg = await message.reply_text(f"🔎 Fetching up to {limit} posts from **{username}** ...")

        posts = await scrape_twitter(username, limit=limit)
        if not posts:
            await msg.edit("⚠️ No media found!")
            return

        total = len(posts)
        for idx, post in enumerate(posts, start=1):
            await msg.edit(f"📤 Uploading {idx}/{total} from @{username}")

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

        await msg.edit(f"✅ Done! {total} posts uploaded from @{username}")

    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")


# =====================
# 🚀 Run Bot
# =====================
if __name__ == "__main__":
    bot.run()
