import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
import logging
from pathlib import Path
import requests
import re  # Adicione este import no topo do arquivo

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

def atualizar_sistema_para_placa(placa_atual, localizacao_placa):
    logging.info(f"Iniciando atualização no SSW para a placa: {placa_atual}, Localização: {localizacao_placa}")

    edge_options = Options()
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_experimental_option('prefs', {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
        
    driver = None
    try:
        driver = webdriver.Edge(options=edge_options)
        logging.info(f"WebDriver iniciado para placa {placa_atual}.")
        
        # Processo de login (sem loop de tentativas)
        driver.get("https://sistema.ssw.inf.br/bin/ssw0422")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "f1")))
        
        driver.find_element(By.NAME, "f1").send_keys("LDI")
        time.sleep(0.5)
        driver.find_element(By.NAME, "f2").send_keys("12373493977")
        time.sleep(0.5)
        driver.find_element(By.NAME, "f3").send_keys("gustavo")
        time.sleep(0.5)
        driver.find_element(By.NAME, "f4").send_keys("12032006")
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

            for linha in linhas:
                try:
                    celulas = linha.find_elements(By.TAG_NAME, "td")
                    if len(celulas) > 0:
                        texto_linha = linha.text
                        if "AUTORIZADO" in texto_linha:
                            valor_coluna_zero = celulas[0].text
                            # Separa letras dos números usando regex e remove traço dos números
                            match = re.match(r'([A-Za-z]+)([\d-]+)', valor_coluna_zero)
                            if match:
                                manifesto_cta.append(match.group(1))  # Parte das letras (CTA)
                                # Remove o traço e quaisquer caracteres não numéricos
                                numero_limpo = re.sub(r'[^0-9]', '', match.group(2))
                                manifesto_numero.append(numero_limpo)  # Apenas números
                except Exception as e:
                    logging.error(f"Erro ao processar linha: {e}")

            print(f"CTAs: {manifesto_cta}")
            print(f"Números: {manifesto_numero}")
            time.sleep(1)

            # Loop para processar cada manifesto encontrado
            for i in range(len(manifesto_cta)):
                logging.info(f"Processando manifesto {i+1}/{len(manifesto_cta)}: {manifesto_cta[i]} - {manifesto_numero[i]}")
                driver.close()
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
                time.sleep(1)
                driver.find_element(By.NAME, "f3").send_keys("33+")
                time.sleep(1)

                driver.switch_to.window(driver.window_handles[-1])
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "11")))
                driver.find_element(By.ID, "11").send_keys(manifesto_cta[0])
                driver.find_element(By.ID, "12").send_keys(manifesto_numero[0])
                time.sleep(1)
                driver.find_element(By.ID, "13").click()
                time.sleep(1)
                
                driver.switch_to.window(driver.window_handles[-1])
                
            
        except (NoSuchElementException, TimeoutException):
            # Se a tabela não existir, executa este bloco
            logging.info("Tabela não encontrada, executando fluxo alternativo...")
            try:
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
                    driver.find_element(By.ID, "13").click()
                    time.sleep(1)

                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(1)

                    driver.find_element(By.NAME, "f3").send_keys("41")
                    time.sleep(1)
                    driver.find_element(By.NAME, "f6").send_keys(f"em transferência: {localizacao_placa}")
                    time.sleep(0.5)
                    enviar_button = driver.find_element(By.ID, "12")
                    driver.execute_script("arguments[0].click();", enviar_button)
                    time.sleep(1)


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
            logging.warning("Nenhum veículo com localização retornado. Encerrando script.")
            return
        
        logging.info(f"{len(veiculos_com_localizacao)} veículos com localização obtidos.")

        # Iterar sobre cada veículo
        logging.info("Iniciando processamento individual de cada veículo no sistema SSW...")
        for i, veiculo_info in enumerate(veiculos_com_localizacao):
            placa_iter = veiculo_info.get('placa')
            localizacao_iter = veiculo_info.get('Local', 'Localização não especificada')
            
            if not placa_iter:
                logging.warning(f"Veículo {i+1} não possui 'placa'. Pulando processamento: {veiculo_info}")
                continue

            logging.info(f"Processando veículo {i+1}/{len(veiculos_com_localizacao)}: Placa {placa_iter}")
            
            atualizar_sistema_para_placa(placa_iter, localizacao_iter)
            
            if i < len(veiculos_com_localizacao) - 1:
                logging.info("Aguardando intervalo antes do próximo veículo...")
                time.sleep(5)

        logging.info("Todos os veículos listados foram processados.")

    except KeyboardInterrupt:
        logging.info("Execução interrompida pelo usuário.")
    except Exception as e_main:
        logging.error(f"Erro não tratado na função main: {e_main}", exc_info=True)
    finally:
        logging.info("Script principal finalizado.")

if __name__ == "__main__":
    main()