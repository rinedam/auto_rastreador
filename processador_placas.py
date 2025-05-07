import json
import logging
from pathlib import Path

import api_client
import selenium_bot as selenium_bot

LOGS_DIR_PROCESSADOR = Path(__file__).resolve().parent / "logs_processador"
LOGS_DIR_PROCESSADOR.mkdir(exist_ok=True) # Cria o diretório de logs se não existir
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR_PROCESSADOR / "processador.log"),
        logging.StreamHandler()
    ]
)

# ==== FUNÇÃO PRINCIPAL ====

def processar_localizacao_veiculos():
    resultados_finais = []
    
    logging.info("Iniciando o processo de localização de veículos...")

    try:
        placas = selenium_bot.consultar_placas()
        if not placas:
            logging.warning("Nenhuma placa foi retornada pela função consultar_placas(). O JSON final estará vazio.")
        else:
            logging.info(f"Placas recebidas para processamento: {placas}")
    except Exception as e:
        logging.error(f"Falha crítica ao tentar executar consultar_placas() do Selenium: {e}")
        logging.warning("Continuando com uma lista de placas vazia devido ao erro na extração.")
        placas = []

    if not placas:
        logging.info("Nenhuma placa para processar. Encerrando a consulta à API.")
    else:
        token = None
        try:
            logging.info("Obtendo token da API...")
            token = api_client.get_token()
            logging.info("Token da API obtido com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao obter o token da API: {e}. Não será possível consultar as localizações.")
            placas = [] 

        if token:
            for placa in placas:
                logging.info(f"Processando placa: {placa}")
                try:
                    dados_api = api_client.get_ultima_posicao_por_placa(token, placa)
                    if isinstance(dados_api, dict) and 'Posicoes' in dados_api and isinstance(dados_api['Posicoes'], list) and len(dados_api['Posicoes']) > 0:
                        primeira_posicao = dados_api['Posicoes'][0]
                        if isinstance(primeira_posicao, dict) and 'Local' in primeira_posicao:
                            local = primeira_posicao['Local']
                            resultados_finais.append({'placa': placa, 'Local': local})
                            logging.info(f"Localização para {placa}: {local}")
                        else:
                            logging.warning(f"Campo 'Local' não encontrado dentro de 'Posicoes[0]' para a placa {placa}. Resposta: {primeira_posicao}")
                            resultados_finais.append({'placa': placa, 'Local': 'Local não encontrado em Posicoes'})
                    else:
                        logging.warning(f"Estrutura de resposta da API inesperada para a placa {placa} (esperado 'Posicoes' como lista com itens). Resposta: {dados_api}")
                        resultados_finais.append({'placa': placa, 'Local': 'Estrutura de resposta inesperada'})
                
                except Exception as e:
                    logging.error(f"Erro ao consultar a API para a placa {placa}: {e}")
                    resultados_finais.append({"placa": placa, "Local": "Erro na consulta"})

    output_file_path = Path(__file__).resolve().parent / "localizacao_veiculos.json"
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(resultados_finais, f, ensure_ascii=False, indent=4)
        logging.info(f"Resultados salvos em: {output_file_path}")
    except Exception as e:
        logging.error(f"Erro ao salvar o arquivo JSON: {e}")

    return str(output_file_path), resultados_finais

# ==== EXECUÇÃO DO SCRIPT ====

if __name__ == "__main__":
    logging.info("Iniciando script processador_placas.py diretamente.")
    caminho_arquivo, dados = processar_localizacao_veiculos()
    if dados:
        logging.info(f"Processamento concluído. Dados: {dados}")
    else:
        logging.info("Processamento concluído, mas nenhum dado de localização foi obtido.")
    logging.info(f"Arquivo de saída: {caminho_arquivo}")