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
from selenium.common.exceptions import WebDriverException

# --- CONFIGURATION ---
AMU_USER = os.getenv('AMU_USER')
AMU_PASS = os.getenv('AMU_PASS')
TARGET_URL = os.getenv('TARGET_URL')
WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK')

# URL du navigateur (défini par docker-compose)
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
    """
    Fonction principale qui ouvre le navigateur et boucle à l'infini
    en rafraichissant la page.
    """
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
        log("🚀 Démarrage d'une nouvelle session navigateur...")
        driver = webdriver.Remote(
            command_executor=SELENIUM_URL,
            options=chrome_options
        )
        
        log(f"Chargement initial de l'URL...")
        driver.get(TARGET_URL)
        
        # BOUCLE INFINIE (Tant que le navigateur ne plante pas)
        while True:
            # Petite pause pour laisser le site charger/rediriger
            time.sleep(5)

            # --- 1. GESTION COOKIES ---
            try:
                cookie_btn = driver.find_element(By.XPATH, "//button[contains(., 'Accepter') or contains(., 'Close')]")
                cookie_btn.click()
            except:
                pass

            # --- 2. VÉRIFICATION CONNEXION (CAS) ---
            # Si la session a expiré, on sera redirigé ici automatiquement
            is_login_page = "cas.univ-amu.fr" in driver.current_url
            if not is_login_page:
                try:
                    driver.find_element(By.ID, "username")
                    is_login_page = True
                except:
                    pass

            if is_login_page:
                log("🔑 Session expirée ou nouvelle connexion requise...")
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

                log("Attente redirection post-login...")
                WebDriverWait(driver, 60).until(lambda d: "cas.univ-amu.fr" not in d.current_url)
                log("✅ Reconnecté avec succès.")
                time.sleep(3)

            # --- 3. RECHERCHE DU CRÉNEAU ---
            try:
                # On attend le tableau
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))
                
                # SÉLECTEUR CIBLE
                xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
                target_row = driver.find_element(By.XPATH, xpath_row)
                
                # Scroll pour garder la connexion active et voir l'élément
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
                log(f"⚠️ Erreur lecture tableau (Session peut-être expirée, on retentera) : {e}")

            # --- 4. ATTENTE ET RAFRAÎCHISSEMENT ---
            log("💤 Pause 5 min avant rafraîchissement...")
            time.sleep(300)
            
            log("🔄 Rafraîchissement de la page...")
            driver.refresh()

    except Exception as e:
        log(f"💥 Crash critique du navigateur : {e}")
        raise e # On relance l'erreur pour que le main() redémarre tout propre

    finally:
        if driver:
            try:
                driver.quit()
                log("Navigateur fermé proprement.")
            except:
                pass

if __name__ == "__main__":
    log("Démarrage Moniteur v7 (Persistent Session)...")
    
    # Boucle de sécurité : Si le navigateur plante complètement (mémoire, crash réseau...),
    # on attend 1 minute et on relance une toute nouvelle session propre.
    while True:
        try:
            run_browser_session()
        except Exception:
            log("Redémarrage complet du processus dans 60 secondes...")
            time.sleep(60)