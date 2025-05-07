import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
import logging
from pathlib import Path
import requests

import api_client
import selenium_bot
import processador_placas

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True) # Cria o diretório de logs se não existir

# Configuração de logging
LOG_FILE = LOGS_DIR / "extracao.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# ===== FUNÇÕES AUXILIARES =====

def verificar_conexao(url="https://www.google.com/"):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        logging.error(f"Falha de conexão com {url}")
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar conexão: {e}")
        return False

# ===== FUNÇÃO PRINCIPAL =====

def atualizar_sistema():
    # Log de início
    logging.info("Sistema iniciado e pronto para extração.")

    # Configurações do Edge
    edge_options = Options()
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_experimental_option('prefs', {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
        
    # Inicia o processo de extração
    logging.info("Iniciando processo de extração de dados...")
        
    try:
            with webdriver.Edge(options=edge_options) as driver:
                max_tentativas = 3
                tentativa = 0
                
                while tentativa < max_tentativas:
                    try:
                        # Abre o site do SSW
                        driver.get("https://sistema.ssw.inf.br/bin/ssw0422")
                        
                        # Aguarda a página de login
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "f1")))
                        
                        # Preenche o formulário de login
                        driver.find_element(By.NAME, "f1").send_keys("LDI")
                        driver.find_element(By.NAME, "f2").send_keys("41968069020")
                        driver.find_element(By.NAME, "f3").send_keys("botlogdi")
                        driver.find_element(By.NAME, "f4").send_keys("logbotdi")
                        driver.find_element(By.NAME, "f4").send_keys("+")
                        time.sleep(1)
                        
                        # Clica no botão de login
                        login_button = driver.find_element(By.ID, "5")
                        driver.execute_script("arguments[0].click();", login_button)
                        time.sleep(2)
                        
                        # Aguarda a próxima tela e preenche
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "f2")))
                        driver.find_element(By.NAME, "f2").clear()
                        driver.find_element(By.NAME, "f2").send_keys("CTA")
                        driver.find_element(By.NAME, "f3").send_keys("19+")
                        time.sleep(5)
                        
                        # Troca para a nova aba aberta
                        abas = driver.window_handles
                        driver.switch_to.window(abas[-1])
                        
                        
                        # Sai do loop de tentativas
                        break
                        
                    except (TimeoutException, WebDriverException) as e:
                        # Registra erro no log
                        erro_msg = f"Erro: {e}. Tentativa {tentativa + 1} de {max_tentativas}"
                        logging.error(erro_msg)
                        
                        # Incrementa contador de tentativas
                        tentativa += 1
                        
                        # Aguarda antes de tentar novamente (10 min)
                        if tentativa < max_tentativas:
                            logging.warning("Aguardando 10 minutos antes de tentar novamente...")
                            
                            for _ in range(600):  # 10 minutos
                                time.sleep(1)
                        else:
                            logging.error("Número máximo de tentativas excedido.")
                            
    except Exception as e:
        # Registra erro crítico no log
        erro_msg = f"Erro crítico:s {e}"
        logging.error(erro_msg)

def main():
    """Função principal que inicia a extração"""
    try:
        logging.info(f"Iniciando execução automática de extração de dados SSW")
        atualizar_sistema()
    except KeyboardInterrupt:
        logging.info("Execução interrompida pelo usuário")
    except Exception as e:
        logging.error(f"Erro não tratado: {e}")
        raise
    finally:
        logging.info("Programa finalizado")

if __name__ == "__main__":
    main()