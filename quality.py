# quality.py
"""
Post-extraction quality validation module.
Checks for common issues in sliced tables.
v2: Now with proper QualityReport dataclass.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Structured quality check results."""
    # Core metrics
    empty_ratio: float
    confidence_avg: float
    row_consistency: bool
    column_alignment: bool
    text_coverage: float
    overall_score: float
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    table_shape: tuple = (0, 0)
    total_text_items: int = 0
    
    # Warnings/errors
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Column type inference (new!)
    column_types: List[str] = field(default_factory=list)
    
    def is_acceptable(self, threshold: float = 50.0) -> bool:
        """Simple pass/fail check."""
        return self.overall_score >= threshold
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        status = "✅ PASS" if self.is_acceptable() else "❌ FAIL"
        lines = [
            f"Quality Report - {status}",
            f"Score: {self.overall_score:.1f}%",
            f"Shape: {self.table_shape[0]} rows × {self.table_shape[1]} cols",
            f"Empty cells: {self.empty_ratio:.1%}",
            f"OCR confidence: {self.confidence_avg:.1f}%",
            f"Text coverage: {self.text_coverage:.1%}"
        ]
        
        if self.warnings:
            lines.append(f"⚠️ Warnings: {', '.join(self.warnings)}")
        if self.errors:
            lines.append(f"❌ Errors: {', '.join(self.errors)}")
            
        return '\n'.join(lines)


class QualityChecker:
    """Validates extracted table quality."""

    def __init__(self,
                 empty_threshold: float = 0.3,      # >30% empty cells = warn
                 confidence_threshold: float = 70.0, # Avg OCR conf <70% = warn
                 coverage_threshold: float = 0.5):   # <50% text captured = warn
        self.empty_threshold = empty_threshold
        self.confidence_threshold = confidence_threshold
        self.coverage_threshold = coverage_threshold

    def check_extraction(self, 
                        df: pd.DataFrame, 
                        extracted_text: List[Dict[str, Any]], 
                        template: Any) -> QualityReport:
        """
        Run all quality checks.
        
        Args:
            df: Extracted DataFrame
            extracted_text: Original OCR text items
            template: Template used for extraction
            
        Returns:
            QualityReport with all metrics
        """
        warnings = []
        errors = []
        
        # Handle empty DataFrame
        if df.empty:
            errors.append("Empty DataFrame")
            return QualityReport(
                empty_ratio=1.0,
                confidence_avg=0.0,
                row_consistency=False,
                column_alignment=False,
                text_coverage=0.0,
                overall_score=0.0,
                table_shape=(0, 0),
                total_text_items=len(extracted_text),
                errors=errors
            )
        
        # Run checks
        empty_ratio = self._check_empty_cells(df)
        if empty_ratio > self.empty_threshold:
            warnings.append(f"High empty ratio: {empty_ratio:.1%}")
        
        confidence_avg = self._check_ocr_confidence(extracted_text)
        if confidence_avg < self.confidence_threshold:
            warnings.append(f"Low OCR confidence: {confidence_avg:.1f}%")
        
        row_consistency = self._check_row_patterns(df)
        if not row_consistency:
            warnings.append("Inconsistent row patterns")
        
        column_alignment = self._check_column_consistency(df)
        if not column_alignment:
            warnings.append("Poor column alignment")
        
        text_coverage = self._check_coverage(df, extracted_text)
        if text_coverage < self.coverage_threshold:
            warnings.append(f"Low coverage: {text_coverage:.1%}")
        
        # Infer column types (NEW!)
        column_types = self._infer_column_types(df)
        
        # Calculate overall score (bulldozer simple average)
        scores = []
        scores.append(max(0, 1 - (empty_ratio / self.empty_threshold)))
        scores.append(min(1, confidence_avg / 100))
        scores.append(1 if row_consistency else 0)
        scores.append(1 if column_alignment else 0)
        scores.append(min(1, text_coverage / self.coverage_threshold))
        
        overall_score = (sum(scores) / len(scores)) * 100 if scores else 0.0
        
        return QualityReport(
            empty_ratio=empty_ratio,
            confidence_avg=confidence_avg,
            row_consistency=row_consistency,
            column_alignment=column_alignment,
            text_coverage=text_coverage,
            overall_score=overall_score,
            table_shape=df.shape,
            total_text_items=len(extracted_text),
            warnings=warnings,
            errors=errors,
            column_types=column_types
        )

    def _check_empty_cells(self, df: pd.DataFrame) -> float:
        """Calculate ratio of empty cells."""
        total_cells = df.size
        empty_cells = df.isnull().sum().sum() + (df == '').sum().sum()
        ratio = empty_cells / total_cells if total_cells > 0 else 1.0
        logger.debug(f"Empty cells: {empty_cells}/{total_cells} = {ratio:.2%}")
        return ratio

    def _check_ocr_confidence(self, extracted_text: List[Dict[str, Any]]) -> float:
        """Calculate average OCR confidence."""
        confs = [item.get('confidence', 0) for item in extracted_text if 'confidence' in item]
        avg = sum(confs) / len(confs) if confs else 0.0
        logger.debug(f"OCR confidence: avg={avg:.1f}%, n={len(confs)}")
        return avg

    def _check_row_patterns(self, df: pd.DataFrame) -> bool:
        """Check for consistent row lengths."""
        row_lengths = df.apply(lambda row: (row != '').sum(), axis=1)
        unique_lengths = len(set(row_lengths))
        consistent = unique_lengths <= 2  # Allow some variation
        logger.debug(f"Row pattern check: {unique_lengths} unique lengths")
        return consistent

    def _check_column_consistency(self, df: pd.DataFrame) -> bool:
        """
        Enhanced column consistency check.
        Looks for columns that are mostly empty or mostly full.
        """
        # Calculate fill ratio for each column
        col_fill_ratios = []
        for col in df.columns:
            non_empty = (df[col] != '') & df[col].notna()
            fill_ratio = non_empty.mean()
            col_fill_ratios.append(fill_ratio)
            logger.debug(f"Column {col}: {fill_ratio:.1%} filled")
        
        # Check for extreme columns (all empty or all full)
        extreme_cols = sum(1 for r in col_fill_ratios if r < 0.1 or r > 0.9)
        
        # Consistent if no more than 1 extreme column
        consistent = extreme_cols <= 1
        
        if not consistent:
            logger.warning(f"Found {extreme_cols} extreme columns (near empty/full)")
        
        return consistent

    def _check_coverage(self, df: pd.DataFrame, extracted_text: List[Dict[str, Any]]) -> float:
        """Calculate ratio of extracted text captured in final table."""
        # Get all words from table
        table_text = ' '.join(str(cell) for cell in df.values.flatten() if pd.notna(cell))
        table_words = set(table_text.lower().split())
        
        # Get all words from original extraction
        orig_words = set()
        for item in extracted_text:
            orig_words.update(item['text'].lower().split())
        
        # Calculate coverage
        if not orig_words:
            return 0.0
        
        captured = len(table_words & orig_words)
        total = len(orig_words)
        ratio = captured / total
        
        logger.debug(f"Text coverage: {captured}/{total} words = {ratio:.1%}")
        return ratio
    
    def _infer_column_types(self, df: pd.DataFrame) -> List[str]:
        """
        Infer basic column types (text/numeric/mixed/empty).
        Bulldozer approach: simple pattern matching.
        """
        column_types = []
        
        for col in df.columns:
            col_data = df[col].dropna()
            col_data = col_data[col_data != '']
            
            if len(col_data) == 0:
                column_types.append('empty')
                continue
            
            # Check patterns
            numeric_count = 0
            currency_count = 0
            date_count = 0
            
            for val in col_data:
                val_str = str(val).strip()
                
                # Check for numeric (including currency symbols)
                if any(c in val_str for c in '$£€¥'):
                    currency_count += 1
                elif val_str.replace(',', '').replace('.', '').replace('-', '').isdigit():
                    numeric_count += 1
                # Check for date patterns (simple)
                elif '/' in val_str or '-' in val_str:
                    parts = val_str.replace('/', '-').split('-')
                    if len(parts) == 3 and all(p.isdigit() for p in parts):
                        date_count += 1
            
            # Determine type (>70% threshold)
            total = len(col_data)
            if currency_count / total > 0.7:
                column_types.append('currency')
            elif (numeric_count + currency_count) / total > 0.7:
                column_types.append('numeric')
            elif date_count / total > 0.7:
                column_types.append('date')
            else:
                column_types.append('text')
        
        logger.info(f"Inferred column types: {column_types}")
        return column_types