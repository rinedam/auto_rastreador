import requests
import logging
from config import API_BASE_URL, API_USER, API_PASSWORD, API2_BASE_URL, LOCATIONIQ_API_KEY

def get_token():
    data = {
        'grant_type': 'password',
        'username': API_USER,
        'Password': API_PASSWORD # P maiúsculo conforme pede a documentação da API
    }
    base_url = API_BASE_URL if API_BASE_URL.endswith('/') else API_BASE_URL + '/'
    
    response = requests.post(base_url + "Token", data=data, verify=False)
    response.raise_for_status() # Levanta exceção para status HTTP 4xx/5xx
    return response.json()['access_token']

def get_ultima_posicao_por_placa(token, placa):
    headers = {"Authorization": f"Bearer {token}"}
    base_url = API_BASE_URL if API_BASE_URL.endswith('/') else API_BASE_URL + '/'
    endpoint_url = base_url + f"api/v1/UltimaPosicaoVeiculo/ListaUltimaPosicaoPorPlaca"
    
    params = {"placa": placa} # Adicionando o parâmetro placa na URL

    response = requests.get(endpoint_url, headers=headers, params=params, verify=False)
    response.raise_for_status()
    return response.json() # Retorna o JSON completo da resposta da API

def get_cidade_estado_por_coordenadas(latitude, longitude):
    """
    Converte coordenadas em cidade e estado usando a API LocationIQ.
    """
    try:
        params = {
            'key': LOCATIONIQ_API_KEY,
            'lat': latitude,
            'lon': longitude,
            'format': 'json'
        }
        
        response = requests.get(API2_BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        if 'address' in data:
            city = data['address'].get('city') or data['address'].get('town') or data['address'].get('municipality')
            state = data['address'].get('state')
            
            if city and state:
                # Trata o texto da cidade após receber da API
                if "Região Geográfica" in city:
                    city = city.replace("Região Geográfica Imediata de", "").strip()
                    logging.info(f"Nome da cidade ajustado para: {city}")
                
                # Traduz Federal District para Distrito Federal
                if state == "Federal District":
                    state = "Distrito Federal"
                    logging.info("Estado 'Federal District' traduzido para 'Distrito Federal'")
                
                return {'cidade': city, 'estado': state}
                
        logging.warning(f"Dados de endereço incompletos para coordenadas {latitude}, {longitude}")
        return None
        
    except Exception as e:
        logging.error(f"Erro ao converter coordenadas em endereço: {e}")
        return None

