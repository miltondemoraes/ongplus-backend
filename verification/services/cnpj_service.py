import urllib.request
import urllib.error
import json
import logging
from verification.exceptions import CnpjNotFound, ExternalApiError

logger = logging.getLogger(__name__)

def get_cnpj_data(cnpj: str) -> dict:
    """
    Queries the open.cnpja.com API to retrieve NGO registration details.
    
    Returns a normalized dictionary with the following structure:
    {
        "situacao": str,
        "data_abertura": str,
        "cep": str,
        "logradouro": str,
        "numero": str,
        "cidade": str,
        "estado": str,
        "bairro": str,
        "nome_fantasia": str,
        "razao_social": str
    }
    """
    cnpj_digits = ''.join(filter(str.isdigit, str(cnpj)))
    if not cnpj_digits or len(cnpj_digits) not in [13, 14]:
        raise ValueError("CNPJ must contain exactly 13 or 14 digits.")
        
    url = f"https://open.cnpja.com/office/{cnpj_digits}"
    
    try:
        # Define Request with User-Agent to avoid issues
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        # Timeout set to 10 seconds
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            
            status_obj = raw_data.get("status", {})
            status_text = status_obj.get("text", "") if isinstance(status_obj, dict) else str(status_obj)
            
            address_obj = raw_data.get("address", {})
            company_obj = raw_data.get("company", {})
            
            normalized_data = {
                "situacao": status_text.upper() if status_text else "",
                "data_abertura": raw_data.get("founded", ""),
                "cep": address_obj.get("zip", ""),
                "logradouro": address_obj.get("street", ""),
                "numero": address_obj.get("number", ""),
                "cidade": address_obj.get("city", ""),
                "estado": address_obj.get("state", ""),
                "bairro": address_obj.get("district", ""),
                "nome_fantasia": raw_data.get("alias", ""),
                "razao_social": company_obj.get("name", "")
            }
            return normalized_data
            
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error querying CNPJá API: {e.code} for CNPJ {cnpj_digits}")
        if e.code == 404 or e.code == 400:
            raise CnpjNotFound(f"CNPJ {cnpj_digits} not found or invalid.")
        raise ExternalApiError(f"CNPJ API returned HTTP error: {e.code}")
    except urllib.error.URLError as e:
        logger.error(f"URL Error querying CNPJá API: {e.reason} for CNPJ {cnpj_digits}")
        raise ExternalApiError(f"External CNPJ API is unreachable: {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error querying CNPJá API: {e} for CNPJ {cnpj_digits}")
        raise ExternalApiError(f"Failed to query CNPJ API: {str(e)}")
