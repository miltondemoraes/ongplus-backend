import re

class OngValidationSerializer:
    """
    A custom serializer class for NGO validation requests.
    Validates presence and format of the CNPJ.
    """
    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}
        self.validated_data = {}

    def is_valid(self) -> bool:
        self.errors = {}
        self.validated_data = {}
        
        cnpj = self.data.get('cnpj')
        
        if cnpj is None:
            self.errors['cnpj'] = ['This field is required.']
            return False
            
        cnpj_str = str(cnpj).strip()
        
        if not cnpj_str:
            self.errors['cnpj'] = ['This field may not be blank.']
            return False
            
        # Clean the CNPJ to contain only digits
        cnpj_digits = re.sub(r'\D', '', cnpj_str)
        
        # Valid CNPJ length is 14
        if len(cnpj_digits) != 14:
            self.errors['cnpj'] = ['CNPJ must contain exactly 14 digits.']
            return False
            
        self.validated_data['cnpj'] = cnpj_digits
        return True
