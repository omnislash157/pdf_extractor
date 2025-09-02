from PyPDF2 import PdfReader, PdfWriter

def split_pdf(file_path):
    reader = PdfReader(file_path)
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        output_filename = f"{file_path.replace('.pdf', '')}_page{i+1}.pdf"
        with open(output_filename, "wb") as f:
            writer.write(f)
        print(f"Saved {output_filename}")

# 🔥 Replace with your actual filename
split_pdf(r"C:\Users\mhartigan\venv\pdf_extractor\DRISCOLL CF ORDERS FOR THE WEEK OF SEPTEMBER 8, 2025.pdf")
