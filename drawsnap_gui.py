# drawsnap_gui.py
"""
DrawSnap GUI module - visual template creation for table extraction.
Refactored with modular architecture for maintainability.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io
import json
import os
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

print("🚀 DrawSnap GUI Starting (Modular v2.2)")


@dataclass
class DrawingState:
    """Immutable drawing state container."""
    box_coords: Optional[List[int]] = None
    column_coords: List[int] = None
    
    def __post_init__(self):
        if self.column_coords is None:
            self.column_coords = []


class CanvasRenderer:
    """Handles all canvas drawing operations."""
    
    def __init__(self):
        self.canvas_elements = {
            'image_id': None,
            'box_id': None,
            'column_ids': [],
            'temp_box_id': None  # For drag preview
        }
    
    def render_image(self, canvas: tk.Canvas, tk_img: ImageTk.PhotoImage, 
                    scroll_region: Tuple[int, int, int, int]) -> None:
        """Render PDF image on canvas."""
        # Clear only the image, not everything
        if self.canvas_elements['image_id']:
            canvas.delete(self.canvas_elements['image_id'])
        
        self.canvas_elements['image_id'] = canvas.create_image(
            0, 0, anchor="nw", image=tk_img
        )
        canvas.config(scrollregion=scroll_region)
    
    def render_box(self, canvas: tk.Canvas, box_coords: List[int], 
                  scale_factor: float, temporary: bool = False) -> None:
        """Render table box with proper scaling."""
        if not box_coords:
            return
        
        # Scale coordinates for display
        scaled_coords = [int(coord * scale_factor) for coord in box_coords]
        x1, y1, x2, y2 = scaled_coords
        
        # Remove old box
        if temporary and self.canvas_elements['temp_box_id']:
            canvas.delete(self.canvas_elements['temp_box_id'])
        elif not temporary and self.canvas_elements['box_id']:
            canvas.delete(self.canvas_elements['box_id'])
        
        # Draw new box
        box_id = canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="red", width=2, fill="", stipple="gray50"
        )
        
        if temporary:
            self.canvas_elements['temp_box_id'] = box_id
        else:
            self.canvas_elements['box_id'] = box_id
    
    def render_columns(self, canvas: tk.Canvas, column_coords: List[int], 
                      box_coords: List[int], scale_factor: float) -> None:
        """Render column separators with proper scaling."""
        # Clear old columns
        for col_id in self.canvas_elements['column_ids']:
            canvas.delete(col_id)
        self.canvas_elements['column_ids'] = []
        
        if not column_coords or not box_coords:
            return
        
        # Scale coordinates
        scaled_box = [int(coord * scale_factor) for coord in box_coords]
        y1, y2 = scaled_box[1], scaled_box[3]
        
        for col_x in column_coords:
            scaled_x = int(col_x * scale_factor)
            
            # Only draw if within box bounds
            if scaled_box[0] <= scaled_x <= scaled_box[2]:
                line_id = canvas.create_line(
                    scaled_x, y1, scaled_x, y2,
                    fill="blue", width=2
                )
                self.canvas_elements['column_ids'].append(line_id)
    
    def render_all(self, canvas: tk.Canvas, tk_img: Optional[ImageTk.PhotoImage],
                  state: DrawingState, scale_factor: float) -> None:
        """Complete redraw of all elements."""
        # Clear everything cleanly
        self.clear_all(canvas)
        
        if tk_img:
            # Get dimensions from PhotoImage
            width = tk_img.width()
            height = tk_img.height()
            self.render_image(canvas, tk_img, (0, 0, width, height))
        
        if state.box_coords:
            self.render_box(canvas, state.box_coords, scale_factor)
        
        if state.column_coords and state.box_coords:
            self.render_columns(canvas, state.column_coords, 
                              state.box_coords, scale_factor)
    
    def clear_all(self, canvas: tk.Canvas) -> None:
        """Clear all tracked canvas elements."""
        for key, value in self.canvas_elements.items():
            if key == 'column_ids':
                for col_id in value:
                    canvas.delete(col_id)
                self.canvas_elements[key] = []
            elif value:
                canvas.delete(value)
                self.canvas_elements[key] = None


class TemplateSaver:
    """Handles template persistence and vendor management."""
    
    def __init__(self, templates_file: str = 'vendor_templates.json'):
        self.templates_file = templates_file
    
    def save_template(self, box_coords: List[int], column_coords: List[int], 
                     vendor: Optional[str] = None) -> Tuple[bool, str]:
        """
        Save template to JSON file.
        
        Returns:
            (success, message) tuple
        """
        if not box_coords:
            return False, "No table box defined"
        
        # Get vendor name if not provided
        if not vendor:
            vendor = self.prompt_vendor()
            if not vendor:
                return False, "No vendor name provided"
        
        # Prepare column coordinates
        columns = self._prepare_columns(column_coords, box_coords)
        
        # Create template
        template = {
            'table_box': box_coords,
            'columns': columns,
            'vendor': vendor
        }
        
        # Save to file
        try:
            templates = self._load_templates()
            templates[vendor] = template
            
            with open(self.templates_file, 'w') as f:
                json.dump(templates, f, indent=4)
            
            return True, f"Template saved for vendor: {vendor}"
            
        except Exception as e:
            return False, f"Failed to save template: {e}"
    
    def prompt_vendor(self) -> Optional[str]:
        """Prompt user for vendor name."""
        return simpledialog.askstring("Vendor Name", "Enter vendor name:")
    
    def _prepare_columns(self, column_coords: List[int], 
                        box_coords: List[int]) -> List[int]:
        """Prepare column coordinates with boundaries."""
        if not column_coords:
            # Default: full width
            return [box_coords[0], box_coords[2]]
        
        # Sort and add boundaries
        columns = sorted(column_coords)
        
        # Add left boundary if missing
        if columns[0] != box_coords[0]:
            columns.insert(0, box_coords[0])
        
        # Add right boundary if missing
        if columns[-1] != box_coords[2]:
            columns.append(box_coords[2])
        
        return columns
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load existing templates from file."""
        if os.path.exists(self.templates_file):
            with open(self.templates_file, 'r') as f:
                return json.load(f)
        return {}


class StatusManager:
    """Manages status bar updates."""
    
    def __init__(self, status_label: tk.Label):
        self.status_label = status_label
    
    def update(self, message: str, emoji: str = "") -> None:
        """Update status with optional emoji."""
        full_message = f"{emoji} {message}" if emoji else message
        self.status_label.config(text=full_message)
    
    def mode_change(self, mode: str) -> None:
        """Update status for mode changes."""
        messages = {
            'box': "📦 Draw mode: Box - Click and drag to draw table boundary",
            'columns': "📊 Draw mode: Columns - Click to add vertical separators",
            'idle': "Ready - Select a drawing mode"
        }
        self.update(messages.get(mode, "Unknown mode"))


class DrawSnapApp:
    """Main application orchestrator - coordinates modular components."""
    
    def __init__(self, root: tk.Tk, pdf_path: Optional[str] = None, 
                vendor: Optional[str] = None):
        """Initialize application with modular components."""
        self.root = root
        self.root.title("DrawSnap Template Creator 🛠")
        self.root.geometry("1000x700")
        
        # Components
        self.renderer = CanvasRenderer()
        self.saver = TemplateSaver()
        self.status_manager = None  # Created after UI setup
        
        # State
        self.pdf_path = pdf_path
        self.vendor = vendor
        self.original_image = None
        self.tk_img = None
        self.scale_factor = 1.0
        self.zoom_level = tk.StringVar(value="100%")
        self.shift_pressed = False
        self.dpi = 150
        
        # Drawing state
        self.drawing_mode = 'idle'
        self.drawing_state = DrawingState()
        self.drag_start = None
        
        # UI setup
        self._setup_ui()
        self.status_manager = StatusManager(self.status_label)
        
        # Load PDF if provided
        if pdf_path:
            self.load_pdf(pdf_path)
    
    def _setup_ui(self):
        """Create UI elements."""
        # Control frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Main buttons
        tk.Button(control_frame, text="📁 Load PDF", 
                 command=self.load_pdf_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="📦 Draw Table Box", 
                 command=self.start_box_drawing).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="📊 Draw Columns", 
                 command=self.start_column_drawing).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="🗑️ Clear All", 
                 command=self.clear_all).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="💾 Save Template", 
                 command=self.save_template).pack(side=tk.LEFT, padx=2)
        
        # Zoom controls
        zoom_frame = tk.Frame(control_frame)
        zoom_frame.pack(side=tk.LEFT, padx=10)
        tk.Button(zoom_frame, text="➖", command=self.zoom_out, width=3).pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="Fit", command=self.zoom_fit, width=5).pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="➕", command=self.zoom_in, width=3).pack(side=tk.LEFT)
        tk.Label(zoom_frame, textvariable=self.zoom_level, width=6).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(control_frame, text="Load a PDF to begin", 
                                    anchor="w", width=40)
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
        self.canvas = tk.Canvas(canvas_frame, bg="gray90",
                               yscrollcommand=v_scrollbar.set,
                               xscrollcommand=h_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.canvas.yview)
        h_scrollbar.config(command=self.canvas.xview)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Mouse wheel bindings
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
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
        """Load and display PDF."""
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
            self.original_image = Image.open(io.BytesIO(img_bytes))
            
            # Auto-fit on load
            self.zoom_fit()
            
            # Update status
            filename = os.path.basename(pdf_path)
            self.status_manager.update(f"Loaded: {filename}", "✅")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load PDF: {e}")
            self.status_manager.update("Failed to load PDF", "❌")
    
    def zoom_out(self):
        """Zoom out by 20%."""
        if not self.original_image:
            return
        self._apply_zoom(0.8)
    
    def zoom_in(self):
        """Zoom in by 25%."""
        if not self.original_image:
            return
        self._apply_zoom(1.25)
    
    def zoom_fit(self):
        """Fit image to canvas."""
        if not self.original_image:
            return
        
        # Get canvas dimensions
        self.canvas.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w, canvas_h = 800, 600  # Fallback
        
        # Calculate fit scale
        img_w, img_h = self.original_image.size
        fit_scale = min(canvas_w / img_w, canvas_h / img_h) * 0.9
        
        # Apply absolute scale
        self.scale_factor = fit_scale
        self._update_display()
    
    def _apply_zoom(self, factor: float):
        """Apply zoom factor."""
        self.scale_factor *= factor
        self.scale_factor = max(0.2, min(5.0, self.scale_factor))
        self._update_display()
    
    def _update_display(self):
        """Update canvas display with current scale."""
        if not self.original_image:
            return
        
        # Resize image
        new_size = (
            int(self.original_image.width * self.scale_factor),
            int(self.original_image.height * self.scale_factor)
        )
        resized = self.original_image.resize(new_size, Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(resized)
        
        # Update zoom indicator
        self.zoom_level.set(f"{int(self.scale_factor * 100)}%")
        
        # Render everything
        self.renderer.render_all(
            self.canvas, self.tk_img, 
            self.drawing_state, self.scale_factor
        )
    
    def start_box_drawing(self):
        """Switch to box drawing mode."""
        self.drawing_mode = 'box'
        self.status_manager.mode_change('box')
    
    def start_column_drawing(self):
        """Switch to column drawing mode."""
        if not self.drawing_state.box_coords:
            messagebox.showinfo("Info", "Please draw a table box first")
            return
        self.drawing_mode = 'columns'
        self.status_manager.mode_change('columns')
    
    def clear_all(self):
        """Clear all drawings."""
        self.drawing_state = DrawingState()
        self.renderer.clear_all(self.canvas)
        self._update_display()
        self.status_manager.update("Cleared all drawings", "🗑️")
    
    def on_click(self, event):
        """Handle mouse click."""
        # Convert canvas coords to image coords
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self.drawing_mode == 'box':
            self.drag_start = (canvas_x, canvas_y)
            
        elif self.drawing_mode == 'columns' and self.drawing_state.box_coords:
            # Convert to unscaled coordinates
            unscaled_x = int(canvas_x / self.scale_factor)
            
            # Check if within box bounds
            if self.drawing_state.box_coords[0] <= unscaled_x <= self.drawing_state.box_coords[2]:
                # Add column
                new_columns = self.drawing_state.column_coords.copy()
                new_columns.append(unscaled_x)
                self.drawing_state = DrawingState(
                    box_coords=self.drawing_state.box_coords,
                    column_coords=new_columns
                )
                
                # Redraw
                self._update_display()
                self.status_manager.update(f"Added column at x={unscaled_x}", "➕")
    
    def on_drag(self, event):
        """Handle mouse drag."""
        if self.drawing_mode == 'box' and self.drag_start:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Create temporary box for preview
            x1, y1 = self.drag_start
            temp_coords = [
                int(min(x1, canvas_x) / self.scale_factor),
                int(min(y1, canvas_y) / self.scale_factor),
                int(max(x1, canvas_x) / self.scale_factor),
                int(max(y1, canvas_y) / self.scale_factor)
            ]
            
            # Render temporary box
            self.renderer.render_box(self.canvas, temp_coords, 
                                    self.scale_factor, temporary=True)
    
    def on_release(self, event):
        """Handle mouse release."""
        if self.drawing_mode == 'box' and self.drag_start:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            x1, y1 = self.drag_start
            
            # Calculate unscaled coordinates
            box_coords = [
                int(min(x1, canvas_x) / self.scale_factor),
                int(min(y1, canvas_y) / self.scale_factor),
                int(max(x1, canvas_x) / self.scale_factor),
                int(max(y1, canvas_y) / self.scale_factor)
            ]
            
            # Update state
            self.drawing_state = DrawingState(
                box_coords=box_coords,
                column_coords=[]  # Reset columns when new box drawn
            )
            
            self.drag_start = None
            self._update_display()
            
            # Update status
            w = box_coords[2] - box_coords[0]
            h = box_coords[3] - box_coords[1]
            self.status_manager.update(f"Box: {w}×{h}px at ({box_coords[0]},{box_coords[1]})", "📦")
    
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if self.shift_pressed:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def on_shift_mousewheel(self, event):
        """Handle shift+mousewheel for horizontal scroll."""
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def save_template(self):
        """Save the current template."""
        success, message = self.saver.save_template(
            self.drawing_state.box_coords,
            self.drawing_state.column_coords,
            self.vendor
        )
        
        if success:
            messagebox.showinfo("Success", message)
            self.status_manager.update(message, "💾")
            self.root.destroy()
        else:
            if message != "No vendor name provided":  # User cancelled
                messagebox.showwarning("Warning", message)
            self.status_manager.update(message, "⚠️")


def create_template_gui(pdf_path: str, vendor: Optional[str] = None) -> bool:
    """
    Launch template creation GUI.
    
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
    return os.path.exists('vendor_templates.json')


# TODO: Future enhancements for React integration
# - Add WebSocket server for real-time state sync
# - Export drawing state as JSON for front-end consumption
# - Add API endpoints for remote control
# - Implement event bus for decoupled components