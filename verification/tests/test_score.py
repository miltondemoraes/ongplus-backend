from django.test import SimpleTestCase
from verification.services.score_service import calculate_reliability_score

class ScoreCalculationTests(SimpleTestCase):
    """
    Unit tests for checking reliability score calculation logic.
    """
    def test_all_criteria_met(self):
        # CNPJ active (+50), address valid (+25), >5 years (+25) = 100
        score = calculate_reliability_score(cnpj_active=True, address_valid=True, years_of_operation=6)
        self.assertEqual(score, 100)

    def test_cnpj_only(self):
        # CNPJ active (+50), address invalid (0), <=5 years (0) = 50
        score = calculate_reliability_score(cnpj_active=True, address_valid=False, years_of_operation=5)
        self.assertEqual(score, 50)

    def test_address_and_years_only(self):
        # CNPJ inactive (0), address valid (+25), >5 years (+25) = 50
        score = calculate_reliability_score(cnpj_active=False, address_valid=True, years_of_operation=10)
        self.assertEqual(score, 50)

    def test_no_criteria_met(self):
        # CNPJ inactive (0), address invalid (0), <=5 years (0) = 0
        score = calculate_reliability_score(cnpj_active=False, address_valid=False, years_of_operation=3)
        self.assertEqual(score, 0)

    def test_exact_5_years_threshold(self):
        # CNPJ active (+50), address valid (+25), exactly 5 years (0) = 75
        score = calculate_reliability_score(cnpj_active=True, address_valid=True, years_of_operation=5)
        self.assertEqual(score, 75)

    def test_greater_than_5_years(self):
        # CNPJ active (+50), address valid (+25), 6 years (+25) = 100
        score = calculate_reliability_score(cnpj_active=True, address_valid=True, years_of_operation=6)
        self.assertEqual(score, 100)
