import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os
import sys
import logging
from pathlib import Path
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv("credenciais.env")

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"extrator_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def verificar_conexao(url="https://www.google.com/"):
    try:
        response = requests.get(url, timeout=5)
        logging.info(f"Conexão com {url} verificada com sucesso")
        return response.status_code == 200
    except requests.ConnectionError:
        logging.error(f"Falha de conexão com {url}")
        return False
    except Exception as e:
        logging.error(f"Erro ao verificar conexão: {e}")
        return False

def setup_edge_options():
    edge_options = Options()
    # edge_options.add_argument("--headless")  # Optional: run in headless mode
    edge_options.add_argument("--log-level=OFF")
    edge_options.add_argument("--silent")
    edge_options.add_argument("--disable-logging")
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    edge_options.add_experimental_option('useAutomationExtension', False)
    edge_options.add_experimental_option('prefs', {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "logging": {
            "browser": "OFF",
            "performance": "OFF"
        }
    })
    return edge_options

def consultar_placas():
    """Executa a extração de dados e retorna uma lista de placas."""
    placas = []
    
    logging.info("Sistema iniciado e pronto para extração.")
    
    download_folder = os.path.expanduser('C:\\Users\\Administrador\\Downloads') 
    
    logging.info(f"Diretório de download configurado para: {download_folder}. Esta verificação de existência será pulada no sandbox.")

    if not verificar_conexao():
        logging.error("Sem conexão com a internet. Abortando.")
        return placas
        
    if not verificar_conexao("http://vstrack.ddns.net/"):
        logging.warning("Possível problema de conexão com o site de destino")
    
    edge_options = setup_edge_options()
    
    logging.info("Iniciando processo de extração de dados...")
    
    try:
        driver = webdriver.Edge(options=edge_options)
        # Adiciona script para mascarar a automação
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        
        with driver:
            max_tentativas = 3
            tentativa = 0
            
            while tentativa < max_tentativas:
                try:
                    url = "http://vstrack.ddns.net/komando/PosicaoVeiculoRastreamento/Index"
                    logging.info(f"Acessando URL: {url}")
                    driver.get(url)
                    
                    logging.info("Aguardando página de login carregar...")
                    email_field = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.NAME, "Email"))
                    )
                    logging.info("Página de login carregada. Preenchendo credenciais...")
                    
                    # Usando variáveis de ambiente para as credenciais
                    komando_email = os.getenv("KOMANDO_EMAIL", "")
                    komando_password = os.getenv("KOMANDO_PASSWORD", "")
                    
                    email_field.send_keys(komando_email)
                    driver.find_element(By.NAME, "Password").send_keys(komando_password)
                    
                    try:
                        logging.info("Tentando clicar no botão de login por ID...")
                        login_button = driver.find_element(By.ID, "botaoLogin")
                        driver.execute_script("arguments[0].click();", login_button)
                    except NoSuchElementException:
                        try:
                            logging.info("Tentando clicar no botão de login por tipo submit...")
                            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                            driver.execute_script("arguments[0].click();", login_button)
                        except NoSuchElementException:
                            logging.info("Tentando clicar no botão de login por XPath...")
                            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar') or contains(text(), 'Login')]")
                            driver.execute_script("arguments[0].click();", login_button)
                    
                    logging.info("Aguardando redirecionamento após login...")
                    time.sleep(5)
                    logging.info(f"Login concluído. URL atual: {driver.current_url}")
                    
                    logging.info("Iniciando extração de dados...")
                    logging.info("Aguardando carregamento da tabela de dados...")
                    try:
                        from selenium.webdriver.support.ui import Select
                        select_element = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.NAME, "datatablesRastreamentosAtivos_length"))
                        )
                        # Rola até o final da tabela
                        driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
                        select = Select(select_element)
                        select.select_by_value("50")
                        logging.info("Opção de 50 registros por página selecionada")
                        time.sleep(2)
                    except Exception as e:
                        logging.error(f"Erro ao configurar número de registros na tabela: {e}")

                    try:
                        tabela = driver.find_element(By.ID, "datatablesRastreamentosAtivos")
                        linhas = tabela.find_elements(By.TAG_NAME, "tr")

                        placas = []
                        placas_problematicas = []

                        for i, linha in enumerate(linhas):
                            celulas = linha.find_elements(By.TAG_NAME, "td")
                            if len(celulas) > 7:
                                placa_com_traco = celulas[1].text.strip()
                                
                                # Verificar se a placa não está vazia
                                if placa_com_traco:
                                    # Verificar se a placa tem um formato válido antes de processar
                                    if '-' in placa_com_traco:
                                        placa_sem_traco = placa_com_traco.replace('-', '')
                                        if placa_sem_traco:  # Verificar se não ficou vazia após substituição
                                            placas.append(placa_sem_traco)
                                            logging.info(f"Placa processada com sucesso: {placa_com_traco} -> {placa_sem_traco}")
                                        else:
                                            logging.warning(f"Placa ficou vazia após substituir traço: {placa_com_traco}")
                                            placas_problematicas.append(placa_com_traco)
                                    else:
                                        # Se não tem traço, adicionar como está
                                        placas.append(placa_com_traco)
                                        logging.info(f"Placa sem traço adicionada: {placa_com_traco}")
                                else:
                                    logging.warning(f"Célula da placa vazia na linha {i+1}")
                                    
                                    # Tentar obter usando JavaScript como alternativa
                                    try:
                                        placa_js = driver.execute_script("return arguments[0].textContent", celulas[1]).strip()
                                        if placa_js:
                                            if '-' in placa_js:
                                                placa_sem_traco = placa_js.replace('-', '')
                                                if placa_sem_traco:
                                                    placas.append(placa_sem_traco)
                                                    logging.info(f"Placa recuperada via JS: {placa_js} -> {placa_sem_traco}")
                                                else:
                                                    logging.warning(f"Placa via JS ficou vazia após substituir traço: {placa_js}")
                                                    placas_problematicas.append(placa_js)
                                            else:
                                                placas.append(placa_js)
                                                logging.info(f"Placa sem traço via JS adicionada: {placa_js}")
                                    except Exception as e:
                                        logging.error(f"Erro ao tentar recuperar placa via JS: {e}")

                        logging.info(f"Total de placas encontradas: {len(placas)}")
                        for i, placa_item in enumerate(placas, 1):
                            logging.info(f"Placa {i}: {placa_item}")

                        if placas_problematicas:
                            logging.warning(f"Placas com problemas de processamento: {placas_problematicas}")

                    except Exception as e:
                        logging.error(f"Erro ao processar placas: {e}", exc_info=True)
                    
                    break
                    
                except TimeoutException as e:
                    logging.error(f"Timeout ao aguardar elemento na tentativa {tentativa+1}: {e}")
                    tentativa += 1
                except WebDriverException as e:
                    logging.error(f"Erro do WebDriver na tentativa {tentativa+1}: {e}")
                    tentativa += 1
                except NoSuchElementException as e:
                    logging.error(f"Elemento não encontrado na tentativa {tentativa+1}: {e}")
                    tentativa += 1
            
            if tentativa == max_tentativas:
                logging.error("Número máximo de tentativas de login/extração atingido.")

    except Exception as e:
        erro_msg = f"Erro crítico no WebDriver ou Selenium: {e}"
        logging.error(erro_msg, exc_info=True)
    
    return placas


def main():
    """Função principal que inicia a extração"""
    try:
        logging.info(f"Iniciando execução automática de extração de dados Komando")
        placas_extraidas = consultar_placas()
        if placas_extraidas:
            logging.info(f"Placas extraídas com sucesso: {placas_extraidas}")
        else:
            logging.info("Nenhuma placa foi extraída ou ocorreu um erro na extração.")
    except Exception as e:
        logging.error(f"Erro não tratado na função main: {e}", exc_info=True)
        raise
    finally:
        logging.info("Programa finalizado")


if __name__ == "__main__":
    main()
    pass
