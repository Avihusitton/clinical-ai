import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on('console', lambda msg: print(f'CONSOLE: {msg.text}'))
        page.on('pageerror', lambda err: print(f'PAGE ERROR: {err}'))
        
        print('Navigating to root...')
        await page.goto('http://127.0.0.1:8765/')
        await page.wait_for_timeout(2000)
        
        # Create a therapist
        print('Creating therapist...')
        await page.click('#showAddTherapistButton')
        await page.wait_for_timeout(500)
        await page.fill('#newTherapistName', 'Dr. Test')
        await page.click('#addTherapistButton')
        await page.wait_for_timeout(1000)
        
        # Create a patient
        print('Creating patient...')
        await page.click('#showAddPatientButton')
        await page.wait_for_timeout(500)
        await page.fill('#newPatientName', 'Test Patient')
        await page.click('#addPatientButton')
        await page.wait_for_timeout(1000)
        
        # Send question
        print('Typing question...')
        await page.fill('#questionInput', 'החוויה הפנימית של רון עבור רון, העולם החברתי הוא שדה מוקשים פוטנציאלי.')
        await page.click('#askButton')
        
        print('Waiting for stream response...')
        await page.wait_for_timeout(5000)
        
        messages = await page.locator('.message-body').all_text_contents()
        for i, msg in enumerate(messages):
            print(f'Message {i}: {msg}')
            
        loading = await page.locator('.message-loader').count()
        print(f'Loading animation count: {loading}')
        
        await browser.close()

asyncio.run(main())
