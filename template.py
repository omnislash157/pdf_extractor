# template.py
"""
Template management module - handles vendor-specific table extraction templates.
Provides persistence, validation, and vendor auto-detection.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)


@dataclass
class TableTemplate:
    """Table extraction template for a specific vendor."""
    table_box: List[int]  # [x1, y1, x2, y2]
    columns: List[int]    # x-positions of column separators
    vendor: str
    created: Optional[str] = None
    modified: Optional[str] = None
    confidence: float = 1.0  # Template confidence/quality score
    
    def validate(self) -> bool:
        """
        Validate template structure.
        
        Returns:
            True if valid, False otherwise
        """
        # Check table box
        if not self.table_box or len(self.table_box) != 4:
            logger.error(f"Invalid table_box: {self.table_box}")
            return False
        
        x1, y1, x2, y2 = self.table_box
        if x1 >= x2 or y1 >= y2:
            logger.error(f"Invalid box dimensions: {self.table_box}")
            return False
        
        # Check columns
        if not self.columns or len(self.columns) < 2:
            logger.error(f"Invalid columns (need at least 2): {self.columns}")
            return False
        
        # Columns should be sorted and within box bounds
        if self.columns != sorted(self.columns):
            logger.warning("Columns not sorted, auto-sorting")
            self.columns = sorted(self.columns)
        
        # Check columns are within box
        if self.columns[0] < x1 or self.columns[-1] > x2:
            logger.warning(f"Columns {self.columns} exceed box bounds [{x1}, {x2}]")
            # Auto-adjust
            self.columns[0] = max(self.columns[0], x1)
            self.columns[-1] = min(self.columns[-1], x2)
        
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'table_box': self.table_box,
            'columns': self.columns,
            'vendor': self.vendor,
            'created': self.created or datetime.now().isoformat(),
            'modified': datetime.now().isoformat(),
            'confidence': self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TableTemplate':
        """Create from dictionary."""
        return cls(
            table_box=data['table_box'],
            columns=data['columns'],
            vendor=data['vendor'],
            created=data.get('created'),
            modified=data.get('modified'),
            confidence=data.get('confidence', 1.0)
        )


class TemplateManager:
    """Manages vendor templates for table extraction."""
    
    def __init__(self, templates_file: str = 'vendor_templates.json'):
        """
        Initialize template manager.
        
        Args:
            templates_file: Path to JSON file storing templates
        """
        self.templates_file = templates_file
        self.templates: Dict[str, TableTemplate] = {}
        self.load_templates()
    
    def load_templates(self) -> None:
        """Load templates from JSON file."""
        if not os.path.exists(self.templates_file):
            logger.info(f"No templates file found at {self.templates_file}, starting fresh")
            self.templates = {}
            return
        
        try:
            with open(self.templates_file, 'r') as f:
                data = json.load(f)
            
            self.templates = {}
            for vendor, template_data in data.items():
                try:
                    template = TableTemplate.from_dict(template_data)
                    if template.validate():
                        self.templates[vendor.lower()] = template
                        logger.info(f"Loaded template for vendor: {vendor}")
                    else:
                        logger.warning(f"Skipped invalid template for vendor: {vendor}")
                except Exception as e:
                    logger.error(f"Failed to load template for {vendor}: {e}")
            
            logger.info(f"Loaded {len(self.templates)} templates")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in templates file: {e}")
            self.templates = {}
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            self.templates = {}
    
    def save_templates(self, make_backup: bool = True) -> bool:
        """
        Save templates to JSON file atomically.
        
        Args:
            make_backup: Whether to create a backup file (default: True)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {}
            for vendor, template in self.templates.items():
                data[vendor] = template.to_dict()
            
            # Create backup if requested and file exists
            if make_backup and os.path.exists(self.templates_file):
                backup_file = f"{self.templates_file}.backup"
                os.replace(self.templates_file, backup_file)  # Atomic move
                logger.info(f"Created backup: {backup_file}")
            
            # Write to temp file and replace atomically
            tmp_file = f"{self.templates_file}.tmp"
            with open(tmp_file, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_file, self.templates_file)
            
            logger.info(f"Saved {len(self.templates)} templates to {self.templates_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")
            # Attempt to clean up temp file if it exists
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            return False
    
    def get_template(self, vendor: str) -> Optional[TableTemplate]:
        """
        Get template for vendor.
        
        Args:
            vendor: Vendor name
            
        Returns:
            TableTemplate if found, None otherwise
        """
        vendor_key = vendor.lower().strip()
        
        # Direct match
        if vendor_key in self.templates:
            logger.info(f"Found exact template for vendor: {vendor}")
            return self.templates[vendor_key]
        
        # Try fuzzy matching
        close_matches = get_close_matches(vendor_key, self.templates.keys(), n=1, cutoff=0.8)
        if close_matches:
            match = close_matches[0]
            logger.info(f"Found fuzzy match for '{vendor}': '{match}'")
            return self.templates[match]
        
        logger.info(f"No template found for vendor: {vendor}")
        return None
    
    def add_template(self, vendor: str, template: TableTemplate) -> bool:
        """
        Add or update template for vendor.
        
        Args:
            vendor: Vendor name
            template: TableTemplate to add
            
        Returns:
            True if successful, False otherwise
        """
        if not template.validate():
            logger.error(f"Cannot add invalid template for vendor: {vendor}")
            return False
        
        vendor_key = vendor.lower().strip()
        
        # Check if updating existing
        if vendor_key in self.templates:
            logger.info(f"Updating existing template for vendor: {vendor}")
            template.modified = datetime.now().isoformat()
        else:
            logger.info(f"Adding new template for vendor: {vendor}")
            template.created = template.created or datetime.now().isoformat()
        
        template.vendor = vendor
        self.templates[vendor_key] = template
        
        # Auto-save
        return self.save_templates()
    
    def remove_template(self, vendor: str) -> bool:
        """
        Remove template for vendor.
        
        Args:
            vendor: Vendor name
            
        Returns:
            True if removed, False if not found
        """
        vendor_key = vendor.lower().strip()
        
        if vendor_key in self.templates:
            del self.templates[vendor_key]
            logger.info(f"Removed template for vendor: {vendor}")
            self.save_templates()
            return True
        
        logger.warning(f"No template to remove for vendor: {vendor}")
        return False
    
    def list_vendors(self) -> List[str]:
        """
        Get list of vendors with templates.
        
        Returns:
            List of vendor names
        """
        return list(self.templates.keys())
    
    def detect_vendor(self, 
                     extracted_text: List[Dict[str, Any]], 
                     vendor_keywords: Optional[Dict[str, List[str]]] = None) -> Optional[str]:
        """
        Auto-detect vendor from extracted text.
        
        Args:
            extracted_text: List of OCR'd text items
            vendor_keywords: Optional dict of vendor -> keywords mapping
            
        Returns:
            Detected vendor name or None
        """
        if not extracted_text:
            return None
        
        # Combine all text (focus on first page/top of document)
        text_sample = ' '.join(
            item['text'] for item in extracted_text[:50]  # First 50 text items
        ).lower()
        
        # Use provided keywords or default set
        if not vendor_keywords:
            vendor_keywords = {
                'amazon': ['amazon', 'aws', 'amzn'],
                'google': ['google', 'gcp', 'alphabet'],
                'microsoft': ['microsoft', 'azure', 'msft'],
                'apple': ['apple', 'aapl', 'iphone'],
                'walmart': ['walmart', 'wmt'],
            }
        
        # Score each vendor
        scores = {}
        for vendor, keywords in vendor_keywords.items():
            score = sum(
                text_sample.count(keyword.lower()) 
                for keyword in keywords
            )
            if score > 0:
                scores[vendor] = score
        
        # Return highest scoring vendor
        if scores:
            best_vendor = max(scores, key=scores.get)
            logger.info(f"Auto-detected vendor: {best_vendor} (score: {scores[best_vendor]})")
            return best_vendor
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about loaded templates.
        
        Returns:
            Dictionary with template statistics
        """
        if not self.templates:
            return {
                'count': 0,
                'vendors': [],
                'avg_columns': 0,
                'newest': None,
                'oldest': None
            }
        
        # Calculate stats
        column_counts = [len(t.columns) - 1 for t in self.templates.values()]
        dates = [t.created for t in self.templates.values() if t.created]
        
        return {
            'count': len(self.templates),
            'vendors': list(self.templates.keys()),
            'avg_columns': sum(column_counts) / len(column_counts) if column_counts else 0,
            'min_columns': min(column_counts) if column_counts else 0,
            'max_columns': max(column_counts) if column_counts else 0,
            'newest': max(dates) if dates else None,
            'oldest': min(dates) if dates else None
        }
    
    def export_template(self, vendor: str, export_path: str) -> bool:
        """
        Export single template to file.
        
        Args:
            vendor: Vendor name
            export_path: Path to export JSON file
            
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template(vendor)
        if not template:
            logger.error(f"No template found for vendor: {vendor}")
            return False
        
        try:
            with open(export_path, 'w') as f:
                json.dump(template.to_dict(), f, indent=4)
            logger.info(f"Exported template for {vendor} to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export template: {e}")
            return False
    
    def import_template(self, import_path: str, vendor: Optional[str] = None) -> bool:
        """
        Import template from file.
        
        Args:
            import_path: Path to template JSON file
            vendor: Optional vendor name override
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)
            
            template = TableTemplate.from_dict(data)
            
            # Override vendor if specified
            if vendor:
                template.vendor = vendor
            
            return self.add_template(template.vendor, template)
            
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return False