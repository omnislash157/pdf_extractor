# slicer.py
"""
Table slicing module - bins positioned text into rows and columns.
Core bulldozer logic for converting positioned text to structured tables.
v2.3: Enhanced with text splitting for wide spans and overflow detection.
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import logging
import re
from statistics import median

logger = logging.getLogger(__name__)


class TableSlicer:
    """Converts positioned text into structured table using templates."""
    
    def __init__(self, 
                 row_threshold: int = 30,
                 adaptive_threshold: bool = True,
                 buffer_factor: float = 1.2,
                 enable_text_splitting: bool = True,
                 min_overlap_ratio: float = 0.25):
        """
        Args:
            row_threshold: Default pixel threshold for grouping text into same row
            adaptive_threshold: Use adaptive threshold based on median y-gap
            buffer_factor: Multiplier for adaptive threshold (1.2 = 20% buffer)
            enable_text_splitting: Whether to split wide text spans across columns
            min_overlap_ratio: Minimum overlap ratio for column assignment
        """
        self.default_row_threshold = row_threshold
        self.adaptive_threshold = adaptive_threshold
        self.buffer_factor = buffer_factor
        self.enable_text_splitting = enable_text_splitting
        self.min_overlap_ratio = min_overlap_ratio
        
        # Compile regex patterns for unsplittable text types
        self.date_pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$')
        self.code_pattern = re.compile(r'^[A-Z]{2,}[-]?\d+$')
        self.price_pattern = re.compile(r'^\$?\d+\.?\d{0,2}$')
        self.item_code_pattern = re.compile(r'^[A-Z0-9]+-[A-Z0-9]+$')
    
    def slice_to_table(self, 
                       extracted: List[Dict[str, Any]], 
                       table_box: List[int], 
                       columns: List[int],
                       page: Optional[int] = None) -> pd.DataFrame:
        """
        Slice extracted text into table using template.
        
        Args:
            extracted: List of extracted text items with positions
            table_box: [x1, y1, x2, y2] defining table region
            columns: List of x-positions defining column separators
            page: Optional page number to filter (None = all pages)
            
        Returns:
            DataFrame with extracted table data
        """
        # Page filtering
        if page is not None:
            logger.info(f"Filtering for page {page}")
            extracted = [item for item in extracted if item.get('page', 1) == page]
            if not extracted:
                logger.warning(f"No text found on page {page}")
                return pd.DataFrame([[f'No text found on page {page}']])
        
        # Filter text within table box
        in_box = self._filter_in_box(extracted, table_box)
        
        if not in_box:
            logger.warning("No text found in table region")
            return pd.DataFrame([['No text found in table region']])
        
        # Determine row threshold
        if self.adaptive_threshold:
            row_threshold = self._get_adaptive_row_threshold(in_box)
        else:
            row_threshold = self.default_row_threshold
        
        # Group into rows
        rows = self._group_into_rows(in_box, row_threshold)
        
        if not rows:
            logger.warning("No rows could be formed from text")
            return pd.DataFrame([['Unable to form rows from text']])
        
        # Bin each row into columns (with text splitting if enabled)
        table_data = self._bin_into_columns_with_splitting(rows, columns)
        
        # Ensure consistent column count
        if table_data:
            max_cols = max(len(row) for row in table_data)
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
            
            # Merge partial rows
            table_data = self._merge_partial_rows(table_data)
        
        return pd.DataFrame(table_data)
    
    def _filter_in_box(self, 
                       extracted: List[Dict[str, Any]], 
                       table_box: List[int]) -> List[Dict[str, Any]]:
        """Filter text items within table box boundaries."""
        x1, y1, x2, y2 = table_box
        
        in_box = []
        for item in extracted:
            center_x = item['x'] + item.get('width', 0) / 2
            center_y = item['y'] + item.get('height', 0) / 2
            
            if (x1 <= center_x <= x2 and y1 <= center_y <= y2):
                in_box.append(item)
        
        logger.info(f"Filtered {len(in_box)} text items within table box from {len(extracted)} total")
        return in_box
    
    def _get_adaptive_row_threshold(self, 
                                   text_boxes: List[Dict[str, Any]], 
                                   min_gap: float = 5.0,
                                   max_threshold: float = 50.0) -> float:
        """Compute adaptive row threshold from median y-gaps."""
        if not text_boxes:
            logger.warning("No text boxes for adaptive threshold - using default")
            return self.default_row_threshold
        
        y_coords = sorted(set(box.get('y', 0) for box in text_boxes))
        
        if len(y_coords) < 2:
            logger.info("Only one row detected - using default threshold")
            return self.default_row_threshold
        
        gaps = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords) - 1)]
        significant_gaps = [g for g in gaps if g >= min_gap]
        
        if not significant_gaps:
            logger.warning(f"All gaps < {min_gap}px - using default threshold")
            return self.default_row_threshold
        
        median_gap = median(significant_gaps)
        threshold = median_gap * self.buffer_factor
        threshold = min(max(threshold, min_gap), max_threshold)
        
        logger.info(f"Adaptive row threshold: {threshold:.1f}px (median gap: {median_gap:.1f}px)")
        return threshold
    
    def _group_into_rows(self, 
                        items: List[Dict[str, Any]], 
                        row_threshold: float) -> List[List[Dict[str, Any]]]:
        """Group text items into rows based on y-position proximity."""
        if not items:
            return []
        
        items = sorted(items, key=lambda x: x['y'])
        
        rows = []
        current_row = [items[0]]
        current_row_y = items[0]['y']
        
        for item in items[1:]:
            if abs(item['y'] - current_row_y) <= row_threshold:
                current_row.append(item)
                total_width = sum(i.get('width', 1) for i in current_row)
                current_row_y = sum(i['y'] * i.get('width', 1) for i in current_row) / total_width
            else:
                rows.append(current_row)
                current_row = [item]
                current_row_y = item['y']
        
        if current_row:
            rows.append(current_row)
        
        logger.info(f"Grouped {len(items)} text items into {len(rows)} rows")
        return rows
    
    def _is_splittable_text(self, text: str) -> bool:
        """
        Determine if text can be split on whitespace.
        Protected patterns: dates, codes, prices, item codes.
        """
        # Check if text matches any protected pattern
        if (self.date_pattern.match(text) or 
            self.code_pattern.match(text) or 
            self.price_pattern.match(text) or
            self.item_code_pattern.match(text)):
            return False
        
        # Check if text contains whitespace to split on
        return ' ' in text
    
    def _calculate_column_spans(self, left_x: int, width: int, columns: List[int]) -> Tuple[List[int], List[float]]:
        """
        Calculate which columns a text item spans and overlap ratios.
        
        Returns:
            Tuple of (overlapping column indices, overlap ratios)
        """
        right_x = left_x + width
        num_cols = len(columns) - 1
        
        overlapping_cols = []
        overlap_ratios = []
        
        for c in range(num_cols):
            col_left = columns[c]
            col_right = columns[c + 1]
            
            overlap = max(0, min(right_x, col_right) - max(left_x, col_left))
            if overlap > 0:
                overlapping_cols.append(c)
                ratio = overlap / width if width > 0 else 0
                overlap_ratios.append(ratio)
        
        return overlapping_cols, overlap_ratios
    
    def _split_text_to_columns(self, text: str, left_x: int, width: int, 
                               overlapping_cols: List[int], columns: List[int]) -> Dict[int, str]:
        """
        Split text across multiple columns proportionally.
        
        Returns:
            Dictionary mapping column index to text portion
        """
        tokens = text.split()
        if not tokens:
            return {}
        
        # Calculate proportional width for each token
        token_lengths = [len(t) for t in tokens]
        total_length = sum(token_lengths)
        if total_length == 0:
            return {}
        
        pixels_per_char = width / total_length
        
        # Assign tokens to columns
        column_assignments = {}
        current_x = left_x
        
        for token, token_len in zip(tokens, token_lengths):
            token_width = token_len * pixels_per_char
            token_center = current_x + token_width / 2
            
            # Find best column for this token
            assigned = False
            for c in overlapping_cols:
                col_left = columns[c]
                col_right = columns[c + 1]
                if col_left <= token_center < col_right:
                    if c not in column_assignments:
                        column_assignments[c] = []
                    column_assignments[c].append(token)
                    assigned = True
                    break
            
            if not assigned and overlapping_cols:
                # Fallback: assign to nearest overlapping column
                best_col = min(overlapping_cols, 
                             key=lambda c: abs(token_center - (columns[c] + columns[c+1])/2))
                if best_col not in column_assignments:
                    column_assignments[best_col] = []
                column_assignments[best_col].append(token)
            
            current_x += token_width
        
        # Join tokens in each column
        return {col: ' '.join(tokens) for col, tokens in column_assignments.items()}
    
    def _bin_into_columns_with_splitting(self, 
                                    rows: List[List[Dict[str, Any]]], 
                                    columns: List[int]) -> List[List[str]]:
        """Enhanced column binning with text splitting for wide spans."""
    
         # DEBUG: Verify we're in the right method
        logger.warning(f"DEBUG: Using splitting method with {len(columns)-1} columns")
        logger.warning(f"DEBUG: Splitting enabled: {self.enable_text_splitting}")
    
        if not columns or len(columns) < 2:
            logger.warning("Invalid column definition - creating single column")
            return [[' '.join(item['text'] for item in row)] for row in rows]
    
    # ... rest of method
        
        num_cols = len(columns) - 1
        table_data = []
        
        for row_idx, row in enumerate(rows):
            row = sorted(row, key=lambda x: x['x'])
            col_bins = [[] for _ in range(num_cols)]
            
            for item in row:
                text = item.get('text', '').strip()
                if not text:
                    continue
                
                left_x = item['x']
                width = item.get('width', 0)
                
                # Handle zero-width items
                if width == 0:
                    for c in range(num_cols):
                        if columns[c] <= left_x < columns[c + 1]:
                            col_bins[c].append(text)
                            break
                    else:
                        if left_x < columns[0]:
                            col_bins[0].append(text)
                        elif left_x >= columns[-1]:
                            col_bins[-1].append(text)
                    continue
                
                # Calculate column spans
                overlapping_cols, overlap_ratios = self._calculate_column_spans(left_x, width, columns)
                
                # Determine if we should split this text
                spans_multiple = len(overlapping_cols) > 1
                is_splittable = self._is_splittable_text(text) if self.enable_text_splitting else False
                
                if spans_multiple and is_splittable:
                    # Split text across columns
                    split_assignments = self._split_text_to_columns(
                        text, left_x, width, overlapping_cols, columns
                    )
                    
                    for col, col_text in split_assignments.items():
                        col_bins[col].append(col_text)
                    
                    logger.debug(f"Split '{text}' across columns {list(split_assignments.keys())}")
                    
                    # Mark as overflow if it was split
                    item['overflow'] = True
                    
            else:
                # ADD DEBUG LINE HERE:
                if spans_multiple:
                        logger.warning(f"DEBUG: NOT SPLITTING '{text}' - spans {len(overlapping_cols)} cols, splittable={is_splittable}")
                    
                # Assign to single best column
                if overlapping_cols and overlap_ratios:
                    best_idx = overlap_ratios.index(max(overlap_ratios))
                    best_col = overlapping_cols[best_idx]
                    col_bins[best_col].append(text)
                        
                    # Mark as overflow if it spans multiple columns but wasn't split
                    if spans_multiple:
                        item['overflow'] = True
                        logger.debug(f"Wide span '{text}' assigned to col {best_col} (overflow marked)")
                else:
                    # No overlap - use fallback
                    for c in range(num_cols):
                        if columns[c] <= left_x < columns[c + 1]:
                             col_bins[c].append(text)
                            break
            
            # Join text in each column
            col_texts = [' '.join(bin_items) for bin_items in col_bins]
            table_data.append(col_texts)
        
        # Log statistics
        if table_data:
            empty_cells = sum(1 for row in table_data for cell in row if not cell)
            total_cells = len(table_data) * num_cols
            empty_ratio = empty_cells / total_cells
            
            if empty_ratio > 0.5:
                logger.warning(f"High empty cell ratio: {empty_ratio:.1%} ({empty_cells}/{total_cells})")
            else:
                logger.info(f"Table created: {len(table_data)} rows × {num_cols} cols")
        
        return table_data
    
    def _merge_partial_rows(self, table_data: List[List[str]], min_columns: int = 4) -> List[List[str]]:
        """Merge partial rows into previous complete rows."""
        if not table_data:
            return table_data
        
        cleaned_rows = []
        
        for i, row in enumerate(table_data):
            filled_cells = sum(1 for cell in row if cell.strip())
            
            if filled_cells < min_columns and cleaned_rows:
                logger.debug(f"Merging partial row {i} ({filled_cells} filled cells) into previous")
                for j, cell in enumerate(row):
                    if cell.strip():
                        if cleaned_rows[-1][j]:
                            cleaned_rows[-1][j] += ' ' + cell.strip()
                        else:
                            cleaned_rows[-1][j] = cell.strip()
            else:
                cleaned_rows.append(row)
        
        logger.info(f"Merged {len(table_data)} rows into {len(cleaned_rows)} clean rows")
        return cleaned_rows