# drawsnap_gui.py
"""
DrawSnap GUI module - visual template creation for table extraction.
Allows users to draw table boundaries and column separators on PDF preview.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import json
import os
from typing import Optional, Tuple, List

print("🚀 GUI Script Starting")

class DrawSnapApp:
    """GUI application for drawing table extraction templates."""
    
    def __init__(self, root: tk.Tk, pdf_path: Optional[str] = None, vendor: Optional[str] = None):
        """
        Args:
            root: Tkinter root window
            pdf_path: Optional PDF to load immediately
            vendor: Optional vendor name to pre-fill
        """
        self.root = root
        self.root.title("DrawSnap Template Creator 🛠")
        self.root.geometry("1000x700")
        
        # State
        self.pdf_path = pdf_path
        self.vendor = vendor
        self.image = None
        self.original_image = None  # Grok Smash: Base for zoom resizing
        self.tk_img = None
        self.scale_factor = 1.0  # Grok Smash: Starts at 100%
        self.zoom_level = tk.StringVar(value="100%")  # Grok Smash: Live display
        self.shift_pressed = False  # Grok Smash: For horizontal wheel
        self.dpi = 150
        
        # Drawing state
        self.drawing_mode = 'box'  # 'box' or 'columns'
        self.box_rect = None
        self.box_coords = None
        self.column_lines = []
        self.column_coords = []
        
        # UI setup
        self._setup_ui()
        
        # Load PDF if provided
        if pdf_path:
            self.load_pdf(pdf_path)
    
    def _setup_ui(self):
        """Create UI elements."""
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Buttons
        tk.Button(control_frame, text="Load PDF", command=self.load_pdf_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Draw Table Box", command=self.start_box_drawing).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Draw Columns", command=self.start_column_drawing).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Save Template", command=self.save_template).pack(side=tk.LEFT, padx=2)
        
        # Grok Smash: Zoom controls frame
        zoom_frame = tk.Frame(control_frame)
        zoom_frame.pack(side=tk.LEFT, padx=5)
        tk.Button(zoom_frame, text="-", command=self.zoom_out).pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="Fit", command=self.zoom_fit).pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="+", command=self.zoom_in).pack(side=tk.LEFT)
        tk.Label(zoom_frame, textvariable=self.zoom_level).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(control_frame, text="Load a PDF to begin")
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # Canvas with scrollbars
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas
        self.canvas = tk.Canvas(canvas_frame, 
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Grok Smash: Mouse wheel bindings (cross-platform)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows/Mac
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)  # Horizontal
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))  # Linux up
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))   # Linux down
        self.root.bind("<KeyPress-Shift_L>", lambda e: setattr(self, 'shift_pressed', True))
        self.root.bind("<KeyRelease-Shift_L>", lambda e: setattr(self, 'shift_pressed', False))
    
    def load_pdf_dialog(self):
        """Open file dialog to load PDF."""
        filepath = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_pdf(filepath)
    
    def load_pdf(self, pdf_path: str):
        """
        Load and display PDF.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        
        try:
            # Open PDF and get first page
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            
            # Render at specified DPI
            mat = fitz.Matrix(self.dpi/72.0, self.dpi/72.0)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_bytes = pix.tobytes("png")
            self.image = Image.open(io.BytesIO(img_bytes))
            self.original_image = self.image.copy()  # Grok Smash: Base for resizing
            
            # Grok Smash: Auto-fit on load
            self.zoom_fit()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
    
    # Grok Smash: Zoom methods
    def zoom_out(self):
        if not self.original_image:
            return
        self._zoom(0.8)
    
    def zoom_in(self):
        if not self.original_image:
            return
        self._zoom(1.25)
    
    def zoom_fit(self):
        if not self.original_image:
            return
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        img_w, img_h = self.original_image.size
        fit_scale = min(canvas_w / img_w, canvas_h / img_h) * 0.9  # 90% fit with margin
        self._zoom(fit_scale / self.scale_factor)  # Apply relative
    
    def _zoom(self, factor: float):
        self.scale_factor *= factor
        self.scale_factor = max(0.2, min(5.0, self.scale_factor))  # Cap extremes
        new_size = (int(self.original_image.width * self.scale_factor), 
                    int(self.original_image.height * self.scale_factor))
        resized = self.original_image.resize(new_size, Image.LANCZOS)  # High-quality
        self.tk_img = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas_img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, new_size[0], new_size[1]))
        self.zoom_level.set(f"{int(self.scale_factor * 100)}%")
        self._redraw_elements()  # Grok Smash: Stub for redrawing box/columns (expand later)
    
    def _redraw_elements(self):
        # Grok Smash: Placeholder - redraw scaled box and columns here in next P0
        pass
    
    # Grok Smash: Wheel handlers
    def on_mousewheel(self, event):
        if self.shift_pressed:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def start_box_drawing(self):
        self.drawing_mode = 'box'
        self.status_label.config(text="Draw mode: Box - Click and drag to draw")
    
    def start_column_drawing(self):
        self.drawing_mode = 'columns'
        self.status_label.config(text="Draw mode: Columns - Click to add vertical lines")
    
    def clear_all(self):
        if self.box_rect:
            self.canvas.delete(self.box_rect)
            self.box_rect = None
            self.box_coords = None
        
        for line in self.column_lines:
            self.canvas.delete(line)
        self.column_lines = []
        self.column_coords = []
        
        self.status_label.config(text="Cleared all drawings")
    
    def on_click(self, event):
        """Handle mouse click."""
        if self.drawing_mode == 'box':
            self.box_start = (event.x, event.y)
            if self.box_rect:
                self.canvas.delete(self.box_rect)
        elif self.drawing_mode == 'columns' and self.box_coords:
            # Add column line within box bounds
            x = event.x
            y1, y2 = self.box_coords[1], self.box_coords[3]
            
            # Check if x is within box
            if self.box_coords[0] <= x <= self.box_coords[2]:
                line = self.canvas.create_line(x, y1, x, y2, fill="blue", width=2)
                self.column_lines.append(line)
                self.column_coords.append(x)
                self.status_label.config(text=f"Added column at x={x}")
    
    def on_drag(self, event):
        """Handle mouse drag."""
        if self.drawing_mode == 'box' and hasattr(self, 'box_start'):
            # Update box rectangle
            if self.box_rect:
                self.canvas.delete(self.box_rect)
            
            x1, y1 = self.box_start
            x2, y2 = event.x, event.y
            
            self.box_rect = self.canvas.create_rectangle(
                x1, y1, x2, y2, 
                outline="red", width=2, fill="", stipple="gray50"
            )
    
    def on_release(self, event):
        """Handle mouse release."""
        if self.drawing_mode == 'box' and hasattr(self, 'box_start'):
            x1, y1 = self.box_start
            x2, y2 = event.x, event.y
            
            # Normalize coordinates
            self.box_coords = [
                min(x1, x2), min(y1, y2),
                max(x1, x2), max(y2, y2)
            ]
            
            self.status_label.config(text=f"Box: {self.box_coords}")
            delattr(self, 'box_start')
    
    def save_template(self):
        """Save the current template."""
        if not self.box_coords:
            messagebox.showwarning("Incomplete", "Please draw a table box first")
            return
        
        # Get vendor name
        if not self.vendor:
            self.vendor = simpledialog.askstring("Vendor Name", "Enter vendor name:")
            if not self.vendor:
                return
        
        # Prepare column coordinates
        if not self.column_coords:
            # If no columns drawn, create default (full width)
            self.column_coords = [self.box_coords[0], self.box_coords[2]]
        else:
            # Sort and add boundaries
            self.column_coords = sorted(self.column_coords)
            if self.column_coords[0] != self.box_coords[0]:
                self.column_coords.insert(0, self.box_coords[0])
            if self.column_coords[-1] != self.box_coords[2]:
                self.column_coords.append(self.box_coords[2])
        
        # Create template
        template = {
            'table_box': self.box_coords,
            'columns': self.column_coords,
            'vendor': self.vendor
        }
        
        # Save to file
        try:
            # Load existing templates
            templates = {}
            templates_file = 'vendor_templates.json'
            if os.path.exists(templates_file):
                with open(templates_file, 'r') as f:
                    templates = json.load(f)
            
            # Add new template
            templates[self.vendor] = template
            
            # Save
            with open(templates_file, 'w') as f:
                json.dump(templates, f, indent=4)
            
            messagebox.showinfo("Success", f"Template saved for vendor: {self.vendor}")
            
            # Close window
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save template: {e}")


def create_template_gui(pdf_path: str, vendor: Optional[str] = None) -> bool:
    """
    Convenience function to launch template creation GUI.
    
    Args:
        pdf_path: Path to PDF file
        vendor: Optional vendor name
        
    Returns:
        True if template was saved, False otherwise
    """
    root = tk.Tk()
    app = DrawSnapApp(root, pdf_path, vendor)
    root.mainloop()
    
    # Check if template was saved
    import os
    return os.path.exists('vendor_templates.json')