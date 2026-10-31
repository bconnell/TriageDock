"""Run a browser acceptance path through the actual containerized UI.

The screenshot is captured from a fresh, synthetic CI database only.
No secrets, user data or private accounts are used. This script does
not modify any host software or personal files.
"""
import base64
import os
from io import BytesIO
from pathlib import Path

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "http://127.0.0.1:8000"
IMAGE = Path("docs/screenshots/dashboard.webp")


def capture(driver):
    """Save a compact, unaltered view of the actual browser canvas."""
    image = Image.open(BytesIO(driver.get_screenshot_as_png())).convert("RGB")
    IMAGE.parent.mkdir(parents=True, exist_ok=True)
    image.save(IMAGE, "WEBP", quality=79, method=6)
    if os.getenv("EXPORT_IMAGE_LOG") == "1":
        b64 = base64.b64encode(IMAGE.read_bytes()).decode("ascii")
        for index in range(0, len(b64), 3500):
            print("SCREENPART_%03d=%s" % (index // 3500, b64[index:index + 3500]), flush=True)
        print("SCREENEND_%d" % IMAGE.stat().st_size, flush=True)


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    driver = webdriver.Chrome(options=options)
    try:
        driver.set_window_size(1440, 900)
        driver.get(BASE_URL)
        wait = WebDriverWait(driver, 25)
        wait.until(EC.visibility_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").send_keys("demo-operator")
        driver.find_element(By.ID, "password").send_keys("demo-ci-password-2026")
        driver.find_element(By.CSS_SELECTOR, "button.login-submit").click()
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Incident dashboard"))
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "tbody tr")) == 4)
        assert "Elevated gateway latency" in driver.page_source
        assert "Replication lag detected" in driver.page_source
        assert "Cache hit ratio below target" in driver.page_source
        assert "No incidents found" not in driver.find_element(By.CSS_SELECTOR, ".table-card").text
        full_height = driver.execute_script("return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
        driver.set_window_size(1440, max(1000, min(int(full_height) + 40, 1700)))
        driver.execute_script("window.scrollTo(0, 0)")
        capture(driver)

        # Exercise a complete operator transition in the real page.
        driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Open Elevated gateway latency"]').click()
        wait.until(EC.visibility_of_element_located((By.ID, "detail-title")))
        assert "Elevated gateway latency" in driver.find_element(By.ID, "detail-title").text
        driver.find_element(By.XPATH, '//button[contains(text(),"Acknowledge")]').click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".detail-pane .pills"), "Acknowledged"))
        driver.find_element(By.XPATH, '//button[contains(text(),"Resolve incident")]').click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".detail-pane .pills"), "Resolved"))
        assert len(driver.find_elements(By.CSS_SELECTOR, ".detail-actions")) == 0
        driver.find_element(By.CSS_SELECTOR, '[aria-label="Close incident details"]').click()
        for width in (800, 375):
            driver.set_window_size(width, 850)
            logout_button = driver.find_element(By.CSS_SELECTOR, ".top-logout")
            assert logout_button.is_displayed(), f"Sign-out control missing at width {width}"
        print("Real browser login, list, detail, acknowledge, resolve and responsive sign-out passed", flush=True)
        print("Screenshot:", IMAGE.as_posix(), IMAGE.stat().st_size, "bytes", flush=True)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
