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

# URL du navigateur
SELENIUM_URL = os.getenv('SELENIUM_URL', 'http://selenium-chrome:4444/wd/hub')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def send_discord_alert(message, file_path=None):
    if not WEBHOOK_URL: return
    try:
        data = {"content": message}
        if file_path:
            with open(file_path, "rb") as f:
                requests.post(WEBHOOK_URL, data=data, files={"file": f})
        else:
            requests.post(WEBHOOK_URL, data=data)
    except Exception as e:
        log(f"Erreur Discord: {e}")

def run_browser_session():
    chrome_options = Options()
    # Options serveur
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Anti-bot
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = None
    try:
        log("🚀 Démarrage session navigateur...")
        driver = webdriver.Remote(
            command_executor=SELENIUM_URL,
            options=chrome_options
        )
        
        log(f"Chargement de l'URL...")
        driver.get(TARGET_URL)
        
        while True:
            # Petite pause technique
            time.sleep(5)

            # --- 1. GESTION COOKIES ---
            try:
                cookie_btn = driver.find_element(By.XPATH, "//button[contains(., 'Accepter') or contains(., 'Close')]")
                cookie_btn.click()
            except:
                pass

            # --- 2. VÉRIFICATION CONNEXION (CAS) ---
            is_login_page = "cas.univ-amu.fr" in driver.current_url
            if not is_login_page:
                try:
                    driver.find_element(By.ID, "username")
                    is_login_page = True
                except:
                    pass

            if is_login_page:
                log("🔑 Connexion requise...")
                WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.ID, "username")))
                
                driver.find_element(By.ID, "username").clear()
                driver.find_element(By.ID, "username").send_keys(AMU_USER)
                driver.find_element(By.ID, "password").clear()
                driver.find_element(By.ID, "password").send_keys(AMU_PASS)
                
                try:
                    submit_btn = driver.find_element(By.ID, "btn-submit")
                    driver.execute_script("arguments[0].click();", submit_btn)
                except:
                    driver.find_element(By.ID, "password").submit()

                log("Attente redirection...")
                WebDriverWait(driver, 60).until(lambda d: "cas.univ-amu.fr" not in d.current_url)
                log("✅ Connecté.")
                time.sleep(3)

            # --- 3. RECHERCHE DU CRÉNEAU ---
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
                xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
                target_row = driver.find_element(By.XPATH, xpath_row)
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_row)
                
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
                    log("🎉 ALERTE : Place disponible !")
                    driver.save_screenshot("success.png")
                    send_discord_alert(f"🚨 **JUDO DISPO !** {TARGET_URL}", "success.png")
                else:
                    log(f"Statut : Complet ({time.strftime('%H:%M')})")

            except Exception as e:
                log(f"⚠️ Erreur lecture (Session expirée ?) : {e}")

            # --- 4. ATTENTE ACTIVE (KEEP-ALIVE) ---
            # C'EST ICI QUE ÇA CHANGE : On n'attend plus 5 min d'un coup.
            # On attend 5 fois 60 secondes en envoyant un "ping" entre chaque.
            log("💤 Attente 5 min (avec Keep-Alive)...")
            
            for i in range(5): # 5 boucles de 60 secondes
                time.sleep(60)
                try:
                    # On demande le titre juste pour maintenir la connexion active
                    _ = driver.title 
                except Exception as e:
                    log("Connexion perdue pendant l'attente.")
                    raise e # On force le redémarrage immédiat

            log("🔄 Rafraîchissement...")
            driver.refresh()

    except Exception as e:
        log(f"💥 Session terminée : {e}")
        raise e 

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    log("Démarrage Moniteur v8 (Anti-Timeout)...")
    while True:
        try:
            run_browser_session()
        except Exception:
            log("Redémarrage dans 10s...")
            time.sleep(10)