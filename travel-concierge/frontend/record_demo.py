import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

ARTIFACTS_DIR = Path("/config/.gemini/antigravity/brain/0143f6b8-b3c2-4b91-999f-9e3518785e3d")
RECORD_DIR = ARTIFACTS_DIR / "videos"
RECORD_DIR.mkdir(parents=True, exist_ok=True)

async def record_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(RECORD_DIR),
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        print("Navigating to http://localhost:8080...")
        await page.goto("http://localhost:8080")
        await page.wait_for_timeout(2500)

        # Prompt 1: What app does best (Itinerary planning)
        prompt1 = "Plan a 3-day itinerary for Tokyo with top highlights and recommended stay"
        print(f"Sending Prompt 1: {prompt1}")
        await page.fill("#input", prompt1)
        await page.wait_for_timeout(800)
        await page.click("button.send-btn")

        # Wait for agent response
        print("Waiting for response 1...")
        await page.wait_for_timeout(10000)

        # Prompt 2: Richer prompt with tool calls, weather, budget calculation, and image generation
        prompt2 = "Check weather in Tokyo, calculate budget for 3 people, and generate a scenic image of Mount Fuji"
        print(f"Sending Prompt 2: {prompt2}")
        await page.fill("#input", prompt2)
        await page.wait_for_timeout(800)
        await page.click("button.send-btn")

        # Wait for agent response and image rendering
        print("Waiting for response 2...")
        await page.wait_for_timeout(16000)

        # Linger on final screen
        await page.wait_for_timeout(3000)

        # Save video path
        video_path = await page.video.path()
        await context.close()
        await browser.close()

        final_mp4 = ARTIFACTS_DIR / "travel_concierge_demo.mp4"
        if os.path.exists(video_path):
            shutil.copy(video_path, final_mp4)
            print(f"Demo video recorded successfully! Path: {final_mp4}")
            return str(final_mp4)
        else:
            print("Video file not found.")
            return None

if __name__ == "__main__":
    asyncio.run(record_demo())
