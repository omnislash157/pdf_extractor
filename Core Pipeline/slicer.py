# slicer.py
"""
Table slicing module - bins positioned text into rows and columns.
Core bulldozer logic for converting positioned text to structured tables.
v2.2-ready: Enhanced with adaptive row threshold and page filtering prep.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import logging
from statistics import median

logger = logging.getLogger(__name__)


class TableSlicer:
    """Converts positioned text into structured table using templates."""
    
    def __init__(self, 
                 row_threshold: int = 20,
                 adaptive_threshold: bool = True,
                 buffer_factor: float = 1.2):
        """
        Args:
            row_threshold: Default pixel threshold for grouping text into same row
            adaptive_threshold: Use adaptive threshold based on median y-gap
            buffer_factor: Multiplier for adaptive threshold (1.2 = 20% buffer)
        """
        self.default_row_threshold = row_threshold
        self.adaptive_threshold = adaptive_threshold
        self.buffer_factor = buffer_factor
    
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
        # Page filtering prep for v2.2
        if page is not None:
            logger.info(f"Filtering for page {page}")
            extracted = [item for item in extracted if item.get('page', 1) == page]
            if not extracted:
                logger.warning(f"No text found on page {page}")
                return pd.DataFrame([[f'No text found on page {page}']])
        
        # Filter text within table box
        in_box = self._filter_in_box(extracted, table_box)
        
        if not in_box:
            logger.warning("No text found in table region - returning empty cell")
            # Return single-cell fallback
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
        
        # Bin each row into columns
        table_data = self._bin_into_columns(rows, columns)
        
        # Ensure consistent column count
        if table_data:
            max_cols = max(len(row) for row in table_data)
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
        
        return pd.DataFrame(table_data)
    
    def _filter_in_box(self, 
                       extracted: List[Dict[str, Any]], 
                       table_box: List[int]) -> List[Dict[str, Any]]:
        """
        Filter text items within table box boundaries.
        
        Args:
            extracted: All extracted text items
            table_box: [x1, y1, x2, y2] boundaries
            
        Returns:
            Filtered list of text items
        """
        x1, y1, x2, y2 = table_box
        
        in_box = []
        for item in extracted:
            # Check if text center is within box (more forgiving than strict boundaries)
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
        """
        Compute adaptive row threshold from median y-gaps.
        
        Args:
            text_boxes: Text items to analyze
            min_gap: Minimum acceptable gap (below this uses default)
            max_threshold: Maximum threshold to prevent runaway values
            
        Returns:
            Calculated threshold or default
        """
        if not text_boxes:
            logger.warning("No text boxes for adaptive threshold - using default")
            return self.default_row_threshold
        
        # Extract unique y-coordinates (top of each text box)
        y_coords = sorted(set(box.get('y', 0) for box in text_boxes))
        
        if len(y_coords) < 2:
            logger.info("Only one row detected - using default threshold")
            return self.default_row_threshold
        
        # Calculate gaps between consecutive y-coordinates
        gaps = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords) - 1)]
        
        # Filter out tiny gaps (likely same-line elements)
        significant_gaps = [g for g in gaps if g >= min_gap]
        
        if not significant_gaps:
            logger.warning(f"All gaps < {min_gap}px - likely dense table, using default threshold")
            return self.default_row_threshold
        
        # Calculate median of significant gaps
        median_gap = median(significant_gaps)
        
        # Apply buffer factor
        threshold = median_gap * self.buffer_factor
        
        # Clamp to reasonable range (bulldozer safety)
        threshold = min(max(threshold, min_gap), max_threshold)
        
        logger.info(f"Adaptive row threshold: {threshold:.1f}px (median gap: {median_gap:.1f}px, buffer: {self.buffer_factor}x)")
        
        return threshold
    
    def _group_into_rows(self, 
                        items: List[Dict[str, Any]], 
                        row_threshold: float) -> List[List[Dict[str, Any]]]:
        """
        Group text items into rows based on y-position proximity.
        
        Args:
            items: Text items to group
            row_threshold: Pixel threshold for same-row determination
            
        Returns:
            List of rows, each row is a list of text items
        """
        if not items:
            return []
        
        # Sort by y-position
        items = sorted(items, key=lambda x: x['y'])
        
        rows = []
        current_row = [items[0]]
        current_row_y = items[0]['y']
        
        for item in items[1:]:
            # Check if item belongs to current row
            if abs(item['y'] - current_row_y) <= row_threshold:
                current_row.append(item)
                # Update row y to weighted average (optional refinement)
                total_width = sum(i.get('width', 1) for i in current_row)
                current_row_y = sum(i['y'] * i.get('width', 1) for i in current_row) / total_width
            else:
                # Start new row
                rows.append(current_row)
                current_row = [item]
                current_row_y = item['y']
        
        # Add last row
        if current_row:
            rows.append(current_row)
        
        logger.info(f"Grouped {len(items)} text items into {len(rows)} rows")
        
        # Log row statistics for debugging
        if rows:
            row_lengths = [len(row) for row in rows]
            logger.debug(f"Row item counts: min={min(row_lengths)}, max={max(row_lengths)}, avg={sum(row_lengths)/len(row_lengths):.1f}")
        
        return rows
    
    def _bin_into_columns(self, 
                         rows: List[List[Dict[str, Any]]], 
                         columns: List[int]) -> List[List[str]]:
        """
        Bin text items in each row into columns.
        
        Args:
            rows: List of rows with text items
            columns: Column separator x-positions
            
        Returns:
            Table data as list of lists
        """
        if not columns or len(columns) < 2:
            # No valid columns, put everything in one column
            logger.warning("Invalid column definition - creating single column")
            return [[' '.join(item['text'] for item in row)] for row in rows]
        
        num_cols = len(columns) - 1
        table_data = []
        
        for row_idx, row in enumerate(rows):
            # Sort items left to right
            row = sorted(row, key=lambda x: x['x'])
            
            # Initialize column texts
            col_texts = [''] * num_cols
            
            for item in row:
                # Find which column this item belongs to (using center point)
                center_x = item['x'] + item.get('width', 0) / 2
                
                # Find appropriate column
                placed = False
                for c in range(num_cols):
                    if columns[c] <= center_x < columns[c + 1]:
                        if col_texts[c]:
                            col_texts[c] += ' '
                        col_texts[c] += item['text']
                        placed = True
                        break
                
                # If not placed, try edge cases
                if not placed:
                    if center_x < columns[0]:
                        # Before first column - add to first
                        if col_texts[0]:
                            col_texts[0] = item['text'] + ' ' + col_texts[0]
                        else:
                            col_texts[0] = item['text']
                    elif center_x >= columns[-1]:
                        # After last column - add to last
                        if col_texts[-1]:
                            col_texts[-1] += ' '
                        col_texts[-1] += item['text']
            
            # Clean up column texts
            col_texts = [text.strip() for text in col_texts]
            table_data.append(col_texts)
        
        logger.info(f"Created table with {len(table_data)} rows and {num_cols} columns")
        
        # Warn if many empty cells
        if table_data:
            empty_cells = sum(1 for row in table_data for cell in row if not cell)
            total_cells = len(table_data) * num_cols
            empty_ratio = empty_cells / total_cells
            if empty_ratio > 0.5:
                logger.warning(f"High empty cell ratio: {empty_ratio:.1%} ({empty_cells}/{total_cells})")
        
        return table_data