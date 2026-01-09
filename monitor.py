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
# URL du navigateur Selenium (defini dans docker-compose)
SELENIUM_URL = os.getenv('SELENIUM_URL', 'http://selenium-chrome:4444/wd/hub')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def send_discord_alert(message, file_path=None):
    try:
        data = {"content": message}
        files = {}
        if file_path:
            with open(file_path, "rb") as f:
                files = {"file": f}
                requests.post(WEBHOOK_URL, data=data, files=files)
        else:
            requests.post(WEBHOOK_URL, data=data)
    except Exception as e:
        log(f"Erreur envoi Discord: {e}")

def check_sport():
    chrome_options = Options()
    # Options minimales pour le mode Remote
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    # Simulation d'un user-agent standard pour éviter d'être bloqué
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        log("Connexion au navigateur distant...")
        # CONNEXION AU CONTENEUR SELENIUM
        driver = webdriver.Remote(
            command_executor=SELENIUM_URL,
            options=chrome_options
        )
        
        log("Chargement de la page...")
        driver.get(TARGET_URL)
        time.sleep(2)

        # 1. GESTION DU LOGIN CAS
        if "cas.univ-amu.fr" in driver.current_url:
            log("Redirection CAS détectée. Connexion...")
            
            WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "username")))
            
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys(AMU_USER)
            
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys(AMU_PASS)
            
            # Clic JS sur le bouton spécifique
            try:
                submit_btn = driver.find_element(By.ID, "btn-submit")
                driver.execute_script("arguments[0].click();", submit_btn)
                log("Bouton cliqué (JS).")
            except:
                log("Fallback: submit standard.")
                driver.find_element(By.ID, "password").submit()

            log("Attente redirection...")
            WebDriverWait(driver, 30).until(lambda d: "cas.univ-amu.fr" not in d.current_url)
            log("✅ Connexion réussie.")
            time.sleep(3)

        # 2. CIBLAGE DU CRÉNEAU
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
        
        # Votre sélecteur spécifique
        xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
        
        try:
            target_row = driver.find_element(By.XPATH, xpath_row)
            log("✅ Ligne du cours trouvée.")
            
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
                log("ALERTE : Place disponible !")
                driver.save_screenshot("success.png")
                send_discord_alert(f"🚨 **JUDO DISPO !** {TARGET_URL}", "success.png")
            else:
                log(f"Pas de place. ({', '.join(details)})")

        except Exception as e:
            log(f"Ligne introuvable ou erreur analyse: {e}")
            # Debug visuel si besoin
            # driver.save_screenshot("debug.png")

    except Exception as e:
        log(f"Erreur globale script: {e}")
            
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    log("Démarrage v5 (Architecture Selenium Distant)...")
    while True:
        check_sport()
        time.sleep(300)