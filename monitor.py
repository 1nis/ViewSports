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

# Mots clés qui indiquent qu'une place est dispo (ex: le texte du bouton)
SUCCESS_KEYWORDS = ["S'inscrire", "Ajouter", "Inscription"]
# Mot clé qui indique que c'est mort
FAIL_KEYWORD = "Complet"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def send_discord_alert(message):
    try:
        data = {"content": message}
        requests.post(WEBHOOK_URL, json=data)
    except Exception as e:
        log(f"Erreur Discord: {e}")

def check_sport():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # User-agent pour ne pas être détecté comme un bot basique
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        log("Chargement de la page...")
        driver.get(TARGET_URL)

        # 1. GESTION DU LOGIN CAS (Si redirigé)
        if "cas.univ-amu.fr" in driver.current_url:
            log("Redirection CAS détectée. Connexion en cours...")
            
            # Attendre que le champ username soit là
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "username")))
            
            driver.find_element(By.ID, "username").send_keys(AMU_USER)
            driver.find_element(By.ID, "password").send_keys(AMU_PASS)
            
            # Click sur le bouton de soumission (souvent name="submit" ou class="btn-submit")
            # On tente de submit le form directement pour être sûr
            password_field = driver.find_element(By.ID, "password")
            password_field.submit()
            
            log("Identifiants envoyés. Attente de la redirection...")
            time.sleep(5) # Laisser le temps au CAS de rediriger

        # 2. VÉRIFICATION SUR LA PAGE DU SPORT
        # On attend que le body soit chargé
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        page_source = driver.page_source

        # Logique de détection
        found_spot = False
        
        # Cas 1 : On trouve explicitement "S'inscrire"
        for kw in SUCCESS_KEYWORDS:
            if kw in page_text:
                found_spot = True
                log(f"Mot clé positif trouvé : {kw}")
                break
        
        # Cas 2 : Le mot "Complet" a disparu (plus risqué si la page change, mais utile)
        # On ne l'utilise que si on ne trouve pas "Complet" ET qu'on est bien sur la bonne page
        if not found_spot and FAIL_KEYWORD not in page_text:
            # Sécurité : on vérifie qu'on est pas sur une page d'erreur
            if "Erreur" not in page_text and "Service" not in page_text:
                found_spot = True
                log(f"Le mot '{FAIL_KEYWORD}' n'est pas présent !")

        if found_spot:
            log("ALERTE : Place détectée !")
            send_discord_alert(f"🚨 **SPORT AMU DISPO !** \nIl semblerait qu'il y ait de la place !\nLien : {TARGET_URL}")
        else:
            log("Toujours complet...")

    except Exception as e:
        log(f"Erreur script : {e}")
        # Optionnel : envoyer un message Discord si le bot crash pour être prévenu
    finally:
        driver.quit()

if __name__ == "__main__":
    log("Démarrage du monitoring AMU...")
    send_discord_alert("🤖 Bot AMU Sport démarré.")
    
    while True:
        check_sport()
        # Pause de 5 minutes (300s)
        time.sleep(300)