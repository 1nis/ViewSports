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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # AJOUT : Définir une taille de fenêtre pour éviter les crashs de rendu
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        log("Chargement de la page...")
        driver.get(TARGET_URL)
        
        # Petite pause pour laisser le temps au DOM de s'initialiser
        time.sleep(2)

        # 1. GESTION DU LOGIN CAS
        if "cas.univ-amu.fr" in driver.current_url:
            log("Redirection CAS détectée. Connexion...")
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
            driver.find_element(By.ID, "username").send_keys(AMU_USER)
            driver.find_element(By.ID, "password").send_keys(AMU_PASS)
            driver.find_element(By.ID, "password").submit()
            log("Connexion envoyée, attente...")
            time.sleep(5)

        # 2. CIBLAGE PRÉCIS DU CRÉNEAU
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))

        # Sélecteur spécifique pour Lundi 18:30 + JASSAUD
        xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
        
        try:
            target_row = driver.find_element(By.XPATH, xpath_row)
            log("✅ Créneau trouvé dans le tableau.")
            
            buttons = target_row.find_elements(By.TAG_NAME, "a")
            place_disponible = False
            details = []

            for btn in buttons:
                texte_bouton = btn.text.strip()
                if not texte_bouton: continue
                
                if "Complet" not in texte_bouton:
                    place_disponible = True
                    details.append(f"Dispo: '{texte_bouton}'")
                else:
                    details.append("Complet")

            if place_disponible:
                log("ALERTE : Une place est libérée !")
                # On prend une photo pour preuve
                driver.save_screenshot("success.png")
                send_discord_alert(
                    f"🚨 **JUDO DISPO !**\nLien : {TARGET_URL}", 
                    "success.png"
                )
            else:
                log(f"Pas de place. ({', '.join(details)})")

        except Exception as e:
            log(f"⚠️ Ligne du cours introuvable. Erreur: {e}")
            driver.save_screenshot("error_row.png")
            send_discord_alert("⚠️ Erreur : Je ne trouve pas la ligne du cours", "error_row.png")

    except Exception as e:
        log(f"Erreur CRITIQUE script : {e}")
        # En cas de crash, on tente le screenshot ultime
        try:
            driver.save_screenshot("crash.png")
            send_discord_alert(f"☠️ Le bot a crashé. Voici ce qu'il voyait : {e}", "crash.png")
        except:
            log("Impossible de prendre le screenshot du crash.")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    log("Démarrage v2 (Debug + Fix Shm)...")
    while True:
        check_sport()
        time.sleep(300)