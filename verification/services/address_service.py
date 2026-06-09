import urllib.request
import urllib.error
import json
import logging
from django.conf import settings
from decouple import config
from verification.exceptions import ExternalApiError

logger = logging.getLogger(__name__)

def get_address_by_cep(cep: str) -> dict:
    """
    Queries an address API (CEP) to obtain official address data.
    Attempts to use the Correios API if a token is configured in environment/settings,
    and falls back to ViaCEP as a highly stable, public alternative.
    
    Returns a normalized dictionary with the following structure:
    {
        "cep": str,
        "logradouro": str,
        "bairro": str,
        "cidade": str,
        "estado": str
    }
    Or None if the CEP does not exist.
    """
    cep_digits = ''.join(filter(str.isdigit, str(cep)))
    if not cep_digits or len(cep_digits) != 8:
        raise ValueError("CEP must contain exactly 8 digits.")

    # 1. Try Correios API if token is configured
    correios_token = getattr(settings, 'CORREIOS_TOKEN', config('CORREIOS_TOKEN', default=None))
    if correios_token:
        try:
            url = f"https://api.correios.com.br/cep/v1/enderecos/{cep_digits}"
            req = urllib.request.Request(
                url,
                headers={
                    'accept': 'application/json',
                    'Authorization': f'Bearer {correios_token}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    "cep": data.get("cep", cep_digits).replace("-", ""),
                    "logradouro": data.get("logradouro", ""),
                    "bairro": data.get("bairro", ""),
                    "cidade": data.get("localidade", data.get("cidade", "")),
                    "estado": data.get("uf", data.get("estado", ""))
                }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info(f"CEP {cep_digits} not found in Correios API.")
                return None
            logger.warning(f"Failed to fetch address from Correios API (HTTP {e.code}). Falling back to ViaCEP.")
        except Exception as e:
            logger.warning(f"Error querying Correios API: {e}. Falling back to ViaCEP.")

    # 2. Fallback to ViaCEP (no auth, highly reliable for dev/test/production)
    try:
        url = f"https://viacep.com.br/ws/{cep_digits}/json/"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('erro'):
                # CEP does not exist
                logger.info(f"CEP {cep_digits} not found in ViaCEP.")
                return None
            
            return {
                "cep": data.get("cep", "").replace("-", ""),
                "logradouro": data.get("logradouro", ""),
                "bairro": data.get("bairro", ""),
                "cidade": data.get("localidade", ""),
                "estado": data.get("uf", "")
            }
    except Exception as e:
        logger.error(f"Failed to fetch address from ViaCEP fallback: {e}")
        raise ExternalApiError(f"Error querying address API for CEP {cep_digits}: {e}")
