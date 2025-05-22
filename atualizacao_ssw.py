import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import logging
from pathlib import Path
import requests
import re  # Adicione este import no topo do arquivo
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv("credenciais.env")

# Importa o processador_placas para obter os dados
import processador_placas 

# Configuração de diretórios
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configuração de logging
LOG_FILE = LOGS_DIR / "atualizacao_ssw_v3.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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

def setup_edge_options():
    edge_options = Options()
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

def atualizar_sistema_para_placa(placa_atual, cidade, estado):
    """
    Atualiza o sistema SSW para uma placa específica usando cidade e estado.
    """
    logging.info(f"Iniciando atualização no SSW para a placa: {placa_atual} - {cidade}/{estado}")

    edge_options = setup_edge_options()
        
    driver = None
    try:
        driver = webdriver.Edge(options=edge_options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })
        logging.info(f"WebDriver iniciado para placa {placa_atual}.")
        
        # Obter credenciais do SSW das variáveis de ambiente
        ssw_empresa = os.getenv("SSW_EMPRESA", "")
        ssw_cnpj = os.getenv("SSW_CNPJ", "")
        ssw_usuario = os.getenv("SSW_USUARIO", "")
        ssw_senha = os.getenv("SSW_SENHA", "")
        
        # Processo de login (sem loop de tentativas)
        driver.get("https://sistema.ssw.inf.br/bin/ssw0422")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "f1")))
        
        driver.find_element(By.NAME, "f1").send_keys(ssw_empresa)
        time.sleep(0.5)
        driver.find_element(By.NAME, "f2").send_keys(ssw_cnpj)
        time.sleep(0.5)
        driver.find_element(By.NAME, "f3").send_keys(ssw_usuario)
        time.sleep(0.5)
        driver.find_element(By.NAME, "f4").send_keys(ssw_senha)
        time.sleep(1)
        login_button = driver.find_element(By.ID, "5")
        driver.execute_script("arguments[0].click();", login_button)
        time.sleep(3)
        
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "f2")))
        driver.find_element(By.NAME, "f2").clear()
        driver.find_element(By.NAME, "f2").send_keys("CTA")
        driver.find_element(By.NAME, "f3").send_keys("23+")
        time.sleep(3)

        # Troca a página para a última aberta
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "t_placa_cavalo")))
        driver.find_element(By.NAME, "t_placa_cavalo").send_keys(placa_atual)
        manifesto_button = driver.find_element(By.ID, "12")
        driver.execute_script("arguments[0].click();", manifesto_button)
        time.sleep(3)

        # Troca a página para a última aberta novamente
        driver.switch_to.window(driver.window_handles[-1])

        try:
            # Tenta encontrar a tabela
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "tblsr")))
            
            # Se a tabela existir, executa este bloco
            logging.info("Tabela encontrada, processando manifestos...")
            manifesto_cta = []  # Lista para armazenar apenas o CTA
            manifesto_numero = []  # Lista para armazenar apenas os números
            tabela = driver.find_element(By.ID, "tblsr")
            linhas = tabela.find_elements(By.TAG_NAME, "tr")

            # Primeiro coleta todos os manifestos autorizados
            for linha in linhas:
                try:
                    celulas = linha.find_elements(By.TAG_NAME, "td")
                    if len(celulas) >= 2:
                        logging.debug(f"Analisando linha com {len(celulas)} células")
                        
                        # Verifica se a penúltima coluna tem valor
                        if len(celulas) > 1 and celulas[-3].text.strip():
                            logging.info(f"Pulando linha - penúltima coluna preenchida: {celulas[-3].text}")
                            continue
                
                        # Pega o manifesto primeiro (primeira coluna)
                        manifesto = celulas[0].text.strip()
                        logging.debug(f"Manifesto encontrado: {manifesto}")
                        
                        # Procura especificamente por AUTORIZADO em vermelho nesta linha
                        autorizado_elements = linha.find_elements(
                            By.XPATH, 
                            ".//font[@color='red' and normalize-space(text())='AUTORIZADO']"
                        )
                        
                        if autorizado_elements:
                            logging.info(f"AUTORIZADO encontrado para manifesto: {manifesto}")
                            # Modifica o regex para capturar corretamente e juntar os números
                            match = re.match(r'([A-Z]{3})\s*(\d+)-?(\d+)?', manifesto)
                            if match:
                                cta = match.group(1)  # Pega CTA
                                numero_principal = match.group(2)  # Pega números antes do traço
                                numero_sufixo = match.group(3) or ''  # Pega números de'pois do traço
                                
                                # Junta os números sem o traço
                                numero_completo = f"{numero_principal}{numero_sufixo}"
                                
                                manifesto_cta.append(cta)
                                manifesto_numero.append(numero_completo)
                                logging.info(f"Manifesto processado e armazenado: CTA={cta}, Número={numero_completo}")
                            else:
                                logging.warning(f"Formato de manifesto não reconhecido: {manifesto}")
                except Exception as e:
                    logging.error(f"Erro ao processar linha: {str(e)}")
                    continue

            # Verificação após processamento
            if manifesto_cta and manifesto_numero:
                logging.info(f"Total de manifestos encontrados: {len(manifesto_cta)}")
                logging.info(f"Manifestos CTA: {manifesto_cta}")
                logging.info(f"Números: {manifesto_numero}")
            else:
                logging.warning("Nenhum manifesto autorizado encontrado")

            # Verifica se encontrou manifestos
            if manifesto_cta and manifesto_numero:
                logging.info(f"Total de manifestos autorizados encontrados: {len(manifesto_cta)}")
                
                # Fecha as duas últimas janelas abertas
                driver.close()
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(1)
                
                # Continua com o processamento usando os valores separados
                driver.find_element(By.NAME, "f3").send_keys("33+")
                time.sleep(1)
                driver.switch_to.window(driver.window_handles[-1])

                # Itera sobre cada manifesto encontrado
                for i in range(len(manifesto_cta)):
                    logging.info(f"Processando manifesto {i+1}/{len(manifesto_cta)}: {manifesto_cta[i]} - {manifesto_numero[i]}")
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "11")))
                    driver.find_element(By.ID, "11").send_keys(manifesto_cta[i])  # Usa o índice i
                    driver.find_element(By.ID, "12").send_keys(manifesto_numero[i])  # Usa o índice i
                    time.sleep(1)
                    janela_atual = driver.current_window_handle
                    driver.find_element(By.ID, "13").click()
                    time.sleep(1)

                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(1)

                    driver.find_element(By.NAME, "f3").send_keys("41")
                    time.sleep(1)
                    driver.find_element(By.NAME, "f4").send_keys(datetime.now().strftime("%d%m%y"))
                    time.sleep(1)
                    driver.find_element(By.NAME, "f5").clear()
                    time.sleep(0.5)
                    driver.find_element(By.NAME, "f5").send_keys(datetime.now().strftime("%H%M"))
                    time.sleep(1)
                    driver.find_element(By.NAME, "f6").send_keys(f"em transf: {cidade} - {estado}")
                    time.sleep(0.5)
                    enviar_button = driver.find_element(By.ID, "9")
                    driver.execute_script("arguments[0].click();", enviar_button)
                    time.sleep(1)
                    driver.switch_to.window(janela_atual)
                    WebDriverWait(driver, 80).until(EC.presence_of_element_located((By.ID, "0")))
                    ok_button = driver.find_element(By.ID, "0")
                    driver.execute_script("arguments[0].click();", ok_button)
                    
                    time.sleep(1)
                    
                logging.info(f"Todos os {len(manifesto_cta)} manifestos foram processados")
            else:
                logging.warning("Nenhum manifesto autorizado encontrado na tabela")

        except (NoSuchElementException, TimeoutException):
            # Se a tabela não existir, executa este bloco
            logging.info("Tabela não encontrada, executando fluxo alternativo...")
            try:
                # Busca todos os elementos <b> da página
                elementos_b = driver.find_elements(By.TAG_NAME, "b")
                
                # Verifica se algum deles contém "CHEGOU" e está em vermelho
                for elemento in elementos_b:
                    if "CHEGOU" in elemento.text:
                        # Verifica se o elemento tem cor vermelha usando JavaScript
                        cor = driver.execute_script("return window.getComputedStyle(arguments[0]).color", elemento)
                        if "rgb(255, 0, 0)" in cor or "red" in cor.lower():
                            logging.info("Encontrado <b>CHEGOU</b> em vermelho, saindo do fluxo...")
                            break
                
                # Busca o form e então o elemento b dentro dele que contém CTA
                form = driver.find_element(By.NAME, "frm")
                elementos_b = form.find_elements(By.TAG_NAME, "b")
                
                manifesto_cta = None
                manifesto_numero = None
                
                for elemento in elementos_b:
                    texto = elemento.text
                    if texto.startswith("CTA"):
                        # Separa letras dos números usando regex e remove traço dos números
                        match = re.match(r'([A-Za-z]+)([\d-]+)', texto)
                        if match:
                            manifesto_cta = match.group(1)  # Parte das letras (CTA)
                            # Remove o traço e quaisquer caracteres não numéricos
                            manifesto_numero = re.sub(r'[^0-9]', '', match.group(2))
                        break
                
                if manifesto_cta and manifesto_numero:
                    logging.info(f"Manifesto encontrado - CTA: {manifesto_cta}, Número: {manifesto_numero}")
                    # Fecha as duas últimas janelas abertas
                    driver.close()
                    driver.switch_to.window(driver.window_handles[-1])
                    driver.close()
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(1)
                    
                    # Continua com o processamento usando os valores separados
                    driver.find_element(By.NAME, "f3").send_keys("33+")
                    time.sleep(1)
                    driver.switch_to.window(driver.window_handles[-1])
                    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "11")))
                    driver.find_element(By.ID, "11").send_keys(manifesto_cta)
                    driver.find_element(By.ID, "12").send_keys(manifesto_numero)
                    time.sleep(1)
                    janela_atual = driver.current_window_handle
                    driver.find_element(By.ID, "13").click()
                    time.sleep(1)

                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(1)

                    driver.find_element(By.NAME, "f3").send_keys("41")
                    time.sleep(1)
                    driver.find_element(By.NAME, "f4").send_keys(datetime.now().strftime("%d%m%y"))
                    time.sleep(1)
                    driver.find_element(By.NAME, "f5").clear()
                    time.sleep(0.5)
                    driver.find_element(By.NAME, "f5").send_keys(datetime.now().strftime("%H%M"))
                    time.sleep(1)
                    driver.find_element(By.NAME, "f6").send_keys(f"em transf: {cidade} - {estado}")
                    time.sleep(0.5)
                    enviar_button = driver.find_element(By.ID, "9")
                    driver.execute_script("arguments[0].click();", enviar_button)
                    time.sleep(1)
                    driver.switch_to.window(janela_atual)
                    WebDriverWait(driver, 80).until(EC.presence_of_element_located((By.ID, "0")))

                else:
                    logging.warning("Nenhum manifesto válido encontrado no formulário")
                    
            except NoSuchElementException:
                logging.error("Formulário 'frm' não encontrado na página")
            except Exception as e:
                logging.error(f"Erro ao buscar manifesto: {e}")


    except Exception as e_geral:
        erro_msg = f"Erro crítico na função atualizar_sistema_para_placa ({placa_atual}): {e_geral}"
        logging.error(erro_msg, exc_info=True)
    finally:
        if driver:
            driver.quit()
            logging.info(f"WebDriver finalizado para placa {placa_atual}.")
        logging.info(f"Função atualizar_sistema_para_placa ({placa_atual}) concluída.")

def main():
    try:
        logging.info("Iniciando script principal...")
        
        # Obter placas e localizações
        logging.info("Consultando placas e localizações via processador_placas.py...")
        _, veiculos_com_localizacao = processador_placas.processar_localizacao_veiculos()

        if not veiculos_com_localizacao:
            logging.warning("Nenhum veículo com localização encontrado. Encerrando processamento.")
            return
        
        total_veiculos = len(veiculos_com_localizacao)
        logging.info(f"Total de {total_veiculos} veículos com localização obtidos.")
        
        # Iterar sobre cada veículo
        for i, veiculo_info in enumerate(veiculos_com_localizacao):
            placa = veiculo_info.get('placa')
            cidade = veiculo_info.get('cidade')
            estado = veiculo_info.get('estado')
            
            if not all([placa, cidade, estado]):
                logging.warning(f"Veículo {i+1} com dados incompletos. Pulando: {veiculo_info}")
                continue
            
            logging.info(f"Processando veículo {i+1}/{total_veiculos}: "
                        f"Placa {placa} - {cidade}/{estado}")
            
            try:
                atualizar_sistema_para_placa(placa, cidade, estado)
                logging.info(f"Veículo {placa} atualizado com sucesso no sistema.")
            except Exception as e:
                logging.error(f"Erro ao atualizar veículo {placa}: {e}")
            
            # Aguarda intervalo entre veículos
            if i < total_veiculos - 1:
                logging.info("Aguardando intervalo de 5 segundos antes do próximo veículo...")
                time.sleep(5)
        
        logging.info("Atualização de todos os veículos concluída com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro não tratado no processo principal: {e}", exc_info=True)
    finally:
        logging.info("Script principal finalizado.")

if __name__ == "__main__":
    main()
