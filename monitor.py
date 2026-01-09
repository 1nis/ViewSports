import time
import os
import sys
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
AMU_USER = os.getenv('AMU_USER')
AMU_PASS = os.getenv('AMU_PASS')
TARGET_URL = os.getenv('TARGET_URL')
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def send_discord_alert(message, file_path=None):
    try:
        data = {"content": message}
        files = {}
        if file_path:
            files = {"file": open(file_path, "rb")}
        requests.post(WEBHOOK_URL, data=data, files=files)
    except Exception as e:
        log(f"Erreur envoi Discord: {e}")

def check_sport():
    chrome_options = Options()
    
    # --- OPTIONS ANTI-CRASH (MODE COMPATIBILITÉ) ---
    # On revient à l'ancien mode headless, plus stable sur les environnements Linux/Docker basiques
    chrome_options.add_argument("--headless") 
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # Options supplémentaires pour éviter les erreurs de rendu (Segfaults)
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-in-process-stack-traces")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log("Chargement de la page...")
        driver.get(TARGET_URL)
        
        time.sleep(3)

        # 1. GESTION DU LOGIN CAS
        if "cas.univ-amu.fr" in driver.current_url:
            log("Redirection CAS détectée. Connexion...")
            
            WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "username")))
            
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys(AMU_USER)
            
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys(AMU_PASS)
            
            # Click JS forcé
            try:
                submit_btn = driver.find_element(By.ID, "btn-submit")
                driver.execute_script("arguments[0].click();", submit_btn)
                log("Bouton cliqué (JS).")
            except:
                log("Bouton introuvable, tentative Enter...")
                driver.find_element(By.ID, "password").submit()

            log("Attente redirection...")
            WebDriverWait(driver, 25).until(lambda d: "cas.univ-amu.fr" not in d.current_url)
            log("✅ Connexion réussie.")
            time.sleep(3)

        # 2. CIBLAGE DU CRÉNEAU
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
        xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
        
        try:
            target_row = driver.find_element(By.XPATH, xpath_row)
            log("✅ Créneau trouvé.")
            
            buttons = target_row.find_elements(By.TAG_NAME, "a")
            place_disponible = False
            details = []

            for btn in buttons:
                txt = btn.text.strip()
                if not txt: continue
                if "Complet" not in txt:
                    place_disponible = True
                    details.append(f"Dispo: '{txt}'")
                else:
                    details.append("Complet")

            if place_disponible:
                log("ALERTE : Place dispo !")
                driver.save_screenshot("success.png")
                send_discord_alert(f"🚨 **JUDO DISPO !** {TARGET_URL}", "success.png")
            else:
                log(f"Pas de place. ({', '.join(details)})")

        except Exception as e:
            log(f"Ligne du cours non trouvée: {e}")
            driver.save_screenshot("debug_row.png")

    except Exception as e:
        log(f"Erreur script: {e}")
        # On évite le screenshot ici s'il y a crash du driver
        send_discord_alert(f"⚠️ Erreur bot: {e}")
            
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    log("Démarrage v4 (Safe Mode)...")
    while True:
        check_sport()
        time.sleep(300)