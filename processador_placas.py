import json
import logging
import time
import api_client
import selenium_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
    handlers=[
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
                        if isinstance(primeira_posicao, dict):
                            # Prioritizando Latitude e Longitude em vez do campo Local
                            latitude = primeira_posicao.get('Latitude')
                            longitude = primeira_posicao.get('Longitude')
                            
                            if latitude is not None and longitude is not None:
                                # Tenta obter cidade e estado das coordenadas
                                localizacao = api_client.get_cidade_estado_por_coordenadas(latitude, longitude)
                                if localizacao:
                                    resultados_finais.append({
                                        'placa': placa,
                                        'cidade': localizacao['cidade'],
                                        'estado': localizacao['estado']
                                    })
                                    time.sleep(1)  # Atraso para evitar sobrecarga na API
                                    logging.info(f"Localização para {placa}: {localizacao['cidade']}, {localizacao['estado']}")
                                else:
                                    # Mantém as coordenadas se não conseguir converter
                                    resultados_finais.append({
                                        'placa': placa,
                                        'Latitude': latitude,
                                        'Longitude': longitude
                                    })
                                    logging.info(f"Mantendo coordenadas para {placa}: Lat={latitude}, Long={longitude}")
                            else:
                                logging.warning(f"Campos 'Latitude' ou 'Longitude' não encontrados para a placa {placa}")
                                resultados_finais.append({
                                    'placa': placa,
                                    'cidade': None,
                                    'estado': None,
                                    'Erro': 'Coordenadas não encontradas'
                                })
                        else:
                            logging.warning(f"Primeira posição não é um dicionário para a placa {placa}. Resposta: {primeira_posicao}")
                            resultados_finais.append({'placa': placa, 'Latitude': None, 'Longitude': None, 'Erro': 'Formato de resposta inválido'})
                    else:
                        logging.warning(f"Estrutura de resposta da API inesperada para a placa {placa} (esperado 'Posicoes' como lista com itens). Resposta: {dados_api}")
                        resultados_finais.append({'placa': placa, 'Latitude': None, 'Longitude': None, 'Erro': 'Estrutura de resposta inesperada'})
                
                except Exception as e:
                    logging.error(f"Erro ao consultar a API para a placa {placa}: {e}")
                    resultados_finais.append({"placa": placa, "Latitude": None, "Longitude": None, "Erro": "Erro na consulta"})

    # Salva o arquivo no diretório atual
    output_file_name = "localizacao_veiculos.json"
    try:
        with open(output_file_name, "w", encoding="utf-8") as f:
            json.dump(resultados_finais, f, ensure_ascii=False, indent=4)
        logging.info(f"Resultados salvos em: {output_file_name}")
    except Exception as e:
        logging.error(f"Erro ao salvar o arquivo JSON: {e}")

    return output_file_name, resultados_finais

# ==== EXECUÇÃO DO SCRIPT ====

if __name__ == "__main__":
    logging.info("Iniciando script processador_placas.py diretamente.")
    caminho_arquivo, dados = processar_localizacao_veiculos()
    if dados:
        logging.info(f"Processamento concluído. Dados: {dados}")
    else:
        logging.info("Processamento concluído, mas nenhum dado de localização foi obtido.")
    logging.info(f"Arquivo de saída: {caminho_arquivo}")