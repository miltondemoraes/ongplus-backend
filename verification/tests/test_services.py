import json
from unittest.mock import MagicMock, patch
import urllib.error
from django.test import TestCase, override_settings
from verification.models import NGO
from verification.exceptions import CnpjNotFound, ExternalApiError
from verification.services.cnpj_service import get_cnpj_data
from verification.services.address_service import get_address_by_cep
from verification.services.validation_service import validate_ngo, calculate_years_of_operation

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def read(self):
        return json.dumps(self.json_data).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class ServiceTests(TestCase):
    """
    Integration and unit tests for services using mocks.
    """

    @patch('urllib.request.urlopen')
    def test_cnpj_service_success(self, mock_urlopen):
        mock_data = {
            "founded": "2015-03-20",
            "status": {"text": "Ativa"},
            "alias": "ONG Teste",
            "company": {"name": "Associacao Ficticia"},
            "address": {
                "zip": "57000000",
                "street": "Rua Principal",
                "number": "123",
                "city": "Maceio",
                "state": "AL",
                "district": "Centro"
            }
        }
        mock_urlopen.return_value = MockResponse(mock_data)
        
        result = get_cnpj_data("12345678000199")
        
        self.assertEqual(result["situacao"], "ATIVA")
        self.assertEqual(result["data_abertura"], "2015-03-20")
        self.assertEqual(result["cep"], "57000000")
        self.assertEqual(result["logradouro"], "Rua Principal")
        self.assertEqual(result["cidade"], "Maceio")
        self.assertEqual(result["estado"], "AL")

    @patch('urllib.request.urlopen')
    def test_cnpj_service_not_found(self, mock_urlopen):
        # Raising HTTPError for 404
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://open.cnpja.com/office/12345678000199",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None
        )
        
        with self.assertRaises(CnpjNotFound):
            get_cnpj_data("12345678000199")

    @patch('urllib.request.urlopen')
    def test_address_service_viacep_success(self, mock_urlopen):
        mock_data = {
            "cep": "57000-000",
            "logradouro": "Rua Principal",
            "bairro": "Centro",
            "localidade": "Maceio",
            "uf": "AL"
        }
        mock_urlopen.return_value = MockResponse(mock_data)
        
        # When CORREIOS_TOKEN is not defined, it directly falls back to ViaCEP
        result = get_address_by_cep("57000000")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["cep"], "57000000")
        self.assertEqual(result["logradouro"], "Rua Principal")
        self.assertEqual(result["cidade"], "Maceio")
        self.assertEqual(result["estado"], "AL")

    def test_calculate_years_of_operation(self):
        self.assertEqual(calculate_years_of_operation("2015-03-20"), date_diff := (2026 - 2015))
        self.assertEqual(calculate_years_of_operation("invalid-date"), 0)
        self.assertEqual(calculate_years_of_operation(""), 0)

    @patch('verification.services.validation_service.get_cnpj_data')
    @patch('verification.services.validation_service.get_address_by_cep')
    def test_full_validation_flow_creates_ngo(self, mock_get_address, mock_get_cnpj):
        # Set up mocks
        mock_get_cnpj.return_value = {
            "situacao": "ATIVA",
            "data_abertura": "2015-03-20",
            "cep": "57000000",
            "logradouro": "Rua Principal",
            "numero": "123",
            "cidade": "Maceio",
            "estado": "AL",
            "bairro": "Centro",
            "razao_social": "Associacao Ficticia"
        }
        
        mock_get_address.return_value = {
            "cep": "57000000",
            "logradouro": "Rua Principal",
            "bairro": "Centro",
            "cidade": "Maceio",
            "estado": "AL"
        }
        
        cnpj = "12345678000199"
        
        # Ensure NGO does not exist initially
        self.assertFalse(NGO.objects.filter(cnpj=cnpj).exists())
        
        result = validate_ngo(cnpj)
        
        # Check validation results
        self.assertTrue(result["cnpj_ativo"])
        self.assertTrue(result["endereco_valido"])
        self.assertEqual(result["score"], 100) # ATIVA (50) + Endereco Valido (25) + >5 anos (25) = 100
        
        # Check database persistence
        ngo = NGO.objects.get(cnpj=cnpj)
        self.assertEqual(ngo.name, "Associacao Ficticia")
        self.assertEqual(ngo.current_score, 100)
        self.assertTrue(ngo.is_active)

    @patch('verification.services.validation_service.get_cnpj_data')
    @patch('verification.services.validation_service.get_address_by_cep')
    def test_full_validation_flow_updates_ngo(self, mock_get_address, mock_get_cnpj):
        cnpj = "12345678000199"
        # Pre-create NGO in DB with low score
        NGO.objects.create(
            cnpj=cnpj,
            name="NGO Teste",
            current_score=10,
            is_active=False
        )
        
        mock_get_cnpj.return_value = {
            "situacao": "ATIVA",
            "data_abertura": "2024-03-20", # 2 years of operation (<=5) -> 0 points
            "cep": "57000000",
            "logradouro": "Rua Principal",
            "numero": "123",
            "cidade": "Maceio",
            "estado": "AL",
            "bairro": "Centro",
            "razao_social": "NGO Teste"
        }
        
        # Address matches
        mock_get_address.return_value = {
            "cep": "57000000",
            "logradouro": "Rua Principal",
            "bairro": "Centro",
            "cidade": "Maceio",
            "estado": "AL"
        }
        
        result = validate_ngo(cnpj)
        
        self.assertEqual(result["score"], 75) # ATIVA (50) + Endereco Valido (25) + <=5 anos (0) = 75
        
        # Check database was updated
        ngo = NGO.objects.get(cnpj=cnpj)
        self.assertEqual(ngo.current_score, 75)
        self.assertTrue(ngo.is_active)

    def test_cnpj_service_invalid_length(self):
        with self.assertRaises(ValueError):
            get_cnpj_data("123")

    @patch('urllib.request.urlopen')
    def test_cnpj_service_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://open.cnpja.com/office/12345678000199",
            code=500, msg="Internal Server Error", hdrs=None, fp=None
        )
        with self.assertRaises(ExternalApiError):
            get_cnpj_data("12345678000199")

    @patch('urllib.request.urlopen')
    def test_cnpj_service_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        with self.assertRaises(ExternalApiError):
            get_cnpj_data("12345678000199")

    @patch('urllib.request.urlopen')
    def test_cnpj_service_generic_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Generic")
        with self.assertRaises(ExternalApiError):
            get_cnpj_data("12345678000199")

    def test_address_service_invalid_length(self):
        with self.assertRaises(ValueError):
            get_address_by_cep("123")

    @patch('urllib.request.urlopen')
    def test_address_service_viacep_not_found(self, mock_urlopen):
        mock_data = {"erro": True}
        mock_urlopen.return_value = MockResponse(mock_data)
        
        result = get_address_by_cep("57000000")
        self.assertIsNone(result)

    @patch('urllib.request.urlopen')
    def test_address_service_viacep_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Generic")
        with self.assertRaises(ExternalApiError):
            get_address_by_cep("57000000")

    @override_settings(CORREIOS_TOKEN='fake_token')
    @patch('urllib.request.urlopen')
    def test_address_service_correios_success(self, mock_urlopen):
        mock_data = {
            "cep": "57000000",
            "logradouro": "Rua Principal C",
            "bairro": "Centro C",
            "localidade": "Maceio C",
            "uf": "AL"
        }
        mock_urlopen.return_value = MockResponse(mock_data)
        
        result = get_address_by_cep("57000000")
        self.assertEqual(result["logradouro"], "Rua Principal C")

    @override_settings(CORREIOS_TOKEN='fake_token')
    @patch('urllib.request.urlopen')
    def test_address_service_correios_not_found(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=404, msg="Not Found", hdrs=None, fp=None
        )
        result = get_address_by_cep("57000000")
        self.assertIsNone(result)

    @override_settings(CORREIOS_TOKEN='fake_token')
    @patch('urllib.request.urlopen')
    def test_address_service_correios_http_fallback(self, mock_urlopen):
        # First call: Correios (fails with 500)
        # Second call: ViaCEP (succeeds)
        mock_urlopen.side_effect = [
            urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None),
            MockResponse({
                "cep": "57000-000", "logradouro": "Rua Principal V", "bairro": "Centro", "localidade": "Maceio", "uf": "AL"
            })
        ]
        result = get_address_by_cep("57000000")
        self.assertEqual(result["logradouro"], "Rua Principal V")

    @override_settings(CORREIOS_TOKEN='fake_token')
    @patch('urllib.request.urlopen')
    def test_address_service_correios_exception_fallback(self, mock_urlopen):
        # First call: Correios (fails with Exception)
        # Second call: ViaCEP (succeeds)
        mock_urlopen.side_effect = [
            Exception("Generic Correios Error"),
            MockResponse({
                "cep": "57000-000", "logradouro": "Rua Principal VE", "bairro": "Centro", "localidade": "Maceio", "uf": "AL"
            })
        ]
        result = get_address_by_cep("57000000")
        self.assertEqual(result["logradouro"], "Rua Principal VE")
