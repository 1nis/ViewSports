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
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        log("Chargement de la page...")
        driver.get(TARGET_URL)

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
        # On attend que le tableau soit chargé
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "tr")))

        # C'est ici la magie : XPath qui cherche la ligne contenant Lundi + 18:30 + JASSAUD
        # Cela garantit qu'on ne regarde pas le mauvais cours
        xpath_row = "//tr[contains(., 'Lundi') and contains(., '18:30') and contains(., 'JASSAUD')]"
        
        try:
            target_row = driver.find_element(By.XPATH, xpath_row)
            log("✅ Créneau 'Lundi 18:30 Jassaud' trouvé dans le tableau.")
            
            # On cherche tous les boutons (les balises <a>) dans cette ligne spécifique
            buttons = target_row.find_elements(By.TAG_NAME, "a")
            
            place_disponible = False
            details = []

            for btn in buttons:
                texte_bouton = btn.text.strip()
                # On ignore les boutons vides ou invisibles
                if not texte_bouton:
                    continue
                
                # Si le texte n'est PAS "Complet" (ex: "S'inscrire", "Ajouter", "Panier"...)
                if "Complet" not in texte_bouton:
                    place_disponible = True
                    details.append(f"Un bouton affiche : '{texte_bouton}'")
                else:
                    details.append("Bouton : Complet")

            if place_disponible:
                log("ALERTE : Une place est libérée !")
                send_discord_alert(
                    f"🚨 **JUDO DISPO !**\n"
                    f"Le créneau Lundi 18:30 (Jassaud) semble avoir une place.\n"
                    f"Statuts détectés : {', '.join(details)}\n"
                    f"Lien : {TARGET_URL}"
                )
            else:
                log(f"Pas de place. Statuts : {', '.join(details)}")

        except Exception as e:
            log(f"⚠️ Impossible de trouver la ligne du cours spécifique. Le planning a peut-être changé d'affichage ? Erreur : {e}")

    except Exception as e:
        log(f"Erreur générale script : {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    log("Démarrage du monitoring JUDO CIBLÉ...")
    send_discord_alert("🤖 Bot Judo (Lundi 18:30) démarré.")
    
    while True:
        check_sport()
        time.sleep(300) # Vérification toutes les 5 minutes