import os
import logging
import asyncio
import aiohttp
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set in Koyeb env

logging.basicConfig(level=logging.INFO)

async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.read()
            with open(filename, "wb") as f:
                f.write(content)

async def scrape_twitter(username: str, max_tweets=5):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto(f"https://twitter.com/{username}", timeout=60000)
        await page.wait_for_selector("article", timeout=15000)

        tweet_articles = await page.query_selector_all("article")
        count = 0

        for article in tweet_articles:
            if count >= max_tweets:
                break

            text = await article.inner_text()
            media_urls = []

            images = await article.query_selector_all("img")
            for img in images:
                src = await img.get_attribute("src")
                if src and "profile_images" not in src:
                    media_urls.append(src)

            videos = await article.query_selector_all("video")
            for vid in videos:
                src = await vid.get_attribute("src")
                if src:
                    media_urls.append(src)

            if media_urls:
                results.append({
                    "text": text,
                    "media": media_urls[:3]  # Limit media per tweet
                })
                count += 1

        await browser.close()

    return results

async def scrape_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrape <username>")
        return

    username = context.args[0].lstrip('@')
    await update.message.reply_text(f"🔍 Scraping @{username}, please wait...")

    try:
        tweets = await scrape_twitter(username)

        if not tweets:
            await update.message.reply_text("No media tweets found.")
            return

        for idx, tweet in enumerate(tweets, start=1):
            caption = tweet["text"][:1024]  # Telegram caption limit
            media_files = []

            for i, url in enumerate(tweet["media"]):
                ext = ".jpg" if ".jpg" in url else ".mp4"
                fname = f"media_{idx}_{i}{ext}"
                await download_file(url, fname)
                media_files.append(fname)

            media_group = []
            for file in media_files:
                if file.endswith(".mp4"):
                    media_group.append(InputMediaVideo(open(file, "rb")))
                else:
                    media_group.append(InputMediaPhoto(open(file, "rb")))

            if media_group:
                await update.message.reply_media_group(media_group)
                await update.message.reply_text(caption)

            # Cleanup
            for file in media_files:
                os.remove(file)

    except Exception as e:
        logging.error(str(e))
        await update.message.reply_text("❌ Error occurred during scraping.")

def main():
    token = BOT_TOKEN or "PASTE_YOUR_BOT_TOKEN_HERE"
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("scrape", scrape_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
