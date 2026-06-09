def calculate_reliability_score(cnpj_active: bool, address_valid: bool, years_of_operation: int) -> int:
    """
    Calculates the reliability score of an NGO based on specific criteria.
    - CNPJ Active: +50 points
    - Address validated: +25 points
    - More than 5 years of operation: +25 points
    - Maximum score: 100 points
    """
    score = 0
    
    if cnpj_active:
        score += 50
        
    if address_valid:
        score += 25
        
    if years_of_operation > 5:
        score += 25
        
    return min(score, 100)
