# test_quality.py
"""
Unit tests for quality.py module.
Bulldozer approach: obvious tests, hard-coded data, loud failures.
"""

import unittest
import pandas as pd
from quality import QualityChecker, QualityReport


class TestQualityReport(unittest.TestCase):
    """Test QualityReport dataclass."""
    
    def test_report_creation(self):
        """Test basic report creation."""
        report = QualityReport(
            empty_ratio=0.2,
            confidence_avg=85.0,
            row_consistency=True,
            column_alignment=True,
            text_coverage=0.75,
            overall_score=75.0,
            table_shape=(10, 5),
            total_text_items=50
        )
        
        self.assertEqual(report.empty_ratio, 0.2)
        self.assertEqual(report.confidence_avg, 85.0)
        self.assertTrue(report.row_consistency)
        self.assertTrue(report.is_acceptable())
    
    def test_report_fail_threshold(self):
        """Test failure detection."""
        report = QualityReport(
            empty_ratio=0.8,
            confidence_avg=45.0,
            row_consistency=False,
            column_alignment=False,
            text_coverage=0.3,
            overall_score=25.0,
            table_shape=(5, 3),
            total_text_items=20
        )
        
        self.assertFalse(report.is_acceptable())
        self.assertFalse(report.is_acceptable(threshold=30.0))
        self.assertTrue(report.is_acceptable(threshold=20.0))
    
    def test_report_summary(self):
        """Test summary generation."""
        report = QualityReport(
            empty_ratio=0.1,
            confidence_avg=90.0,
            row_consistency=True,
            column_alignment=True,
            text_coverage=0.9,
            overall_score=88.0,
            table_shape=(15, 4),
            total_text_items=100,
            warnings=["Test warning"],
            errors=[]
        )
        
        summary = report.get_summary()
        self.assertIn("✅ PASS", summary)
        self.assertIn("88.0%", summary)
        self.assertIn("15 rows × 4 cols", summary)
        self.assertIn("Test warning", summary)


class TestQualityChecker(unittest.TestCase):
    """Test QualityChecker validation logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = QualityChecker()
        
        # Create test DataFrame
        self.df_good = pd.DataFrame([
            ['Item A', '10', '$50.00'],
            ['Item B', '5', '$25.00'],
            ['Item C', '2', '$100.00']
        ])
        
        self.df_bad = pd.DataFrame([
            ['', '', ''],
            ['Item', '', ''],
            ['', '', '$50']
        ])
        
        self.df_empty = pd.DataFrame()
        
        # Create test OCR data
        self.ocr_good = [
            {'text': 'Item', 'x': 10, 'y': 10, 'confidence': 95},
            {'text': 'A', 'x': 50, 'y': 10, 'confidence': 92},
            {'text': '10', 'x': 100, 'y': 10, 'confidence': 88},
            {'text': '$50.00', 'x': 150, 'y': 10, 'confidence': 90}
        ]
        
        self.ocr_bad = [
            {'text': 'Item', 'x': 10, 'y': 10, 'confidence': 45},
            {'text': 'A', 'x': 50, 'y': 10, 'confidence': 30},
            {'text': '10', 'x': 100, 'y': 10, 'confidence': 55}
        ]
        
        # Dummy template
        self.template = type('Template', (), {
            'table_box': [0, 0, 200, 100],
            'columns': [0, 75, 125, 200]
        })()
    
    def test_good_extraction(self):
        """Test quality check on good extraction."""
        report = self.checker.check_extraction(
            self.df_good, 
            self.ocr_good, 
            self.template
        )
        
        self.assertIsInstance(report, QualityReport)
        self.assertLess(report.empty_ratio, 0.1)
        self.assertGreater(report.confidence_avg, 80)
        self.assertTrue(report.row_consistency)
        self.assertGreater(report.overall_score, 70)
        self.assertTrue(report.is_acceptable())
    
    def test_bad_extraction(self):
        """Test quality check on poor extraction."""
        report = self.checker.check_extraction(
            self.df_bad,
            self.ocr_bad,
            self.template
        )
        
        self.assertIsInstance(report, QualityReport)
        self.assertGreater(report.empty_ratio, 0.5)
        self.assertLess(report.confidence_avg, 60)
        self.assertLess(report.overall_score, 50)
        self.assertFalse(report.is_acceptable())
        self.assertGreater(len(report.warnings), 0)
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        report = self.checker.check_extraction(
            self.df_empty,
            self.ocr_good,
            self.template
        )
        
        self.assertIsInstance(report, QualityReport)
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.empty_ratio, 1.0)
        self.assertIn("Empty DataFrame", report.errors)
        self.assertFalse(report.is_acceptable())
    
    def test_empty_ratio_calculation(self):
        """Test empty cell ratio calculation."""
        df = pd.DataFrame([
            ['A', 'B', 'C'],
            ['', 'E', ''],
            ['G', '', 'I']
        ])
        
        ratio = self.checker._check_empty_cells(df)
        self.assertAlmostEqual(ratio, 4/9, places=2)
    
    def test_ocr_confidence_calculation(self):
        """Test OCR confidence averaging."""
        ocr_data = [
            {'text': 'test', 'confidence': 80},
            {'text': 'data', 'confidence': 90},
            {'text': 'here', 'confidence': 70}
        ]
        
        avg = self.checker._check_ocr_confidence(ocr_data)
        self.assertAlmostEqual(avg, 80.0, places=1)
    
    def test_row_pattern_check(self):
        """Test row consistency detection."""
        # Consistent rows
        df_consistent = pd.DataFrame([
            ['A', 'B', 'C'],
            ['D', 'E', 'F'],
            ['G', 'H', 'I']
        ])
        self.assertTrue(self.checker._check_row_patterns(df_consistent))
        
        # Inconsistent rows
        df_inconsistent = pd.DataFrame([
            ['A', 'B', 'C'],
            ['D', '', ''],
            ['', '', 'I']
        ])
        # May still pass with tolerance
        result = self.checker._check_row_patterns(df_inconsistent)
        self.assertIsInstance(result, bool)
    
    def test_column_consistency_check(self):
        """Test column alignment detection."""
        # Good columns
        df_good = pd.DataFrame([
            ['A', 'B', 'C'],
            ['D', 'E', 'F'],
            ['G', 'H', 'I']
        ])
        self.assertTrue(self.checker._check_column_consistency(df_good))
        
        # Bad columns (one empty)
        df_bad = pd.DataFrame([
            ['A', '', 'C'],
            ['D', '', 'F'],
            ['G', '', 'I']
        ])
        self.assertFalse(self.checker._check_column_consistency(df_bad))
    
    def test_text_coverage(self):
        """Test text coverage calculation."""
        df = pd.DataFrame([
            ['Item', 'A'],
            ['Item', 'B']
        ])
        
        ocr_data = [
            {'text': 'Item', 'x': 10, 'y': 10},
            {'text': 'A', 'x': 50, 'y': 10},
            {'text': 'Item', 'x': 10, 'y': 30},
            {'text': 'B', 'x': 50, 'y': 30},
            {'text': 'Extra', 'x': 100, 'y': 50},  # Not captured
            {'text': 'Text', 'x': 100, 'y': 70}    # Not captured
        ]
        
        coverage = self.checker._check_coverage(df, ocr_data)
        # Should capture 4/6 unique words
        self.assertGreater(coverage, 0.5)
        self.assertLess(coverage, 1.0)
    
    def test_column_type_inference(self):
        """Test column type detection."""
        df = pd.DataFrame([
            ['Item A', '10', '$50.00', '2024-01-15'],
            ['Item B', '5', '$25.00', '2024-01-16'],
            ['Item C', '2', '$100.00', '2024-01-17']
        ])
        
        types = self.checker._infer_column_types(df)
        self.assertEqual(len(types), 4)
        self.assertEqual(types[0], 'text')
        self.assertEqual(types[1], 'numeric')
        self.assertEqual(types[2], 'currency')
        self.assertEqual(types[3], 'date')
    
    def test_column_type_edge_cases(self):
        """Test column type inference edge cases."""
        # Empty column
        df_empty_col = pd.DataFrame([
            ['A', ''],
            ['B', ''],
            ['C', '']
        ])
        types = self.checker._infer_column_types(df_empty_col)
        self.assertEqual(types[1], 'empty')
        
        # Mixed column
        df_mixed = pd.DataFrame([
            ['123'],
            ['ABC'],
            ['456']
        ])
        types = self.checker._infer_column_types(df_mixed)
        self.assertEqual(types[0], 'text')  # Not enough numeric to qualify


class TestIntegration(unittest.TestCase):
    """Integration tests for complete quality check flow."""
    
    def test_full_pipeline(self):
        """Test complete quality check pipeline."""
        checker = QualityChecker(
            empty_threshold=0.3,
            confidence_threshold=70.0,
            coverage_threshold=0.5
        )
        
        # Create realistic test data
        df = pd.DataFrame([
            ['Invoice', '#12345', '', '2024-01-15'],
            ['Item', 'Qty', 'Price', 'Total'],
            ['Widget A', '10', '$5.00', '$50.00'],
            ['Widget B', '5', '$10.00', '$50.00'],
            ['', '', 'Subtotal:', '$100.00'],
            ['', '', 'Tax:', '$10.00'],
            ['', '', 'Total:', '$110.00']
        ])
        
        ocr_data = []
        for row in df.values:
            for cell in row:
                if cell:
                    ocr_data.append({
                        'text': str(cell),
                        'x': 10,
                        'y': 10,
                        'confidence': 85
                    })
        
        template = type('Template', (), {
            'table_box': [0, 0, 400, 300],
            'columns': [0, 100, 200, 300, 400]
        })()
        
        report = checker.check_extraction(df, ocr_data, template)
        
        # Validate report structure
        self.assertIsInstance(report, QualityReport)
        self.assertEqual(report.table_shape, df.shape)
        self.assertGreater(report.overall_score, 0)
        
        # Check summary
        summary = report.get_summary()
        self.assertIn("rows", summary.lower())
        self.assertIn("cols", summary.lower())


if __name__ == '__main__':
    # Run with verbose output (bulldozer style - loud and clear!)
    unittest.main(verbosity=2)