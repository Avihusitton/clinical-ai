import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on('console', lambda msg: print(f'CONSOLE: {msg.text}'))
        
        print('Navigating to root...')
        await page.goto('http://127.0.0.1:8765/')
        await page.wait_for_timeout(2000)
        
        # Create a therapist
        await page.click('#showAddTherapistButton')
        await page.wait_for_timeout(500)
        await page.fill('#newTherapistName', 'Dr. Test')
        await page.click('#addTherapistButton')
        await page.wait_for_timeout(1000)
        
        # Create a patient
        await page.click('#showAddPatientButton')
        await page.wait_for_timeout(500)
        await page.fill('#newPatientName', 'Test Patient')
        await page.click('#addPatientButton')
        await page.wait_for_timeout(1000)
        
        await page.fill('#question', 'Hello')
        await page.click('#askButton')
        await page.wait_for_timeout(1000)
        
        err = await page.locator('#composerError').text_content()
        print(f'COMPOSER ERROR: {err.strip() if err else "None"}')
        
        await browser.close()

asyncio.run(main())
