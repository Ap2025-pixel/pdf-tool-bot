import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from PIL import Image
import img2pdf
from pdf2docx import Converter

class PDFTool:
    
    @staticmethod
    def add_watermark(pdf_bytes: bytes, watermark_text: str = "SAMPLE") -> bytes:
        """Add watermark to all pages of a PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            first_page = pdf_reader.pages[0]
            page_width = float(first_page.mediabox.width)
            page_height = float(first_page.mediabox.height)
            
            # Create watermark
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(page_width, page_height))
            c.setFont("Helvetica", 60)
            c.setFillColorRGB(0.5, 0.5, 0.5, 0.3)
            c.saveState()
            c.translate(page_width / 2, page_height / 2)
            c.rotate(45)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            packet.seek(0)
            
            watermark_reader = PdfReader(packet)
            watermark_page = watermark_reader.pages[0]
            
            for page in pdf_reader.pages:
                page.merge_page(watermark_page)
                pdf_writer.add_page(page)
            
            output = io.BytesIO()
            pdf_writer.write(output)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Watermark error: {str(e)}")
    
    @staticmethod
    def remove_pages(pdf_bytes: bytes, pages_to_remove: str) -> bytes:
        """Remove specified pages from PDF"""
        try:
            # Parse page ranges: "6-9" or "1,3,5" or "2-4,7"
            pages = set()
            parts = pages_to_remove.split(',')
            for part in parts:
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    for p in range(start, end + 1):
                        pages.add(p - 1)  # Convert to 0-indexed
                else:
                    pages.add(int(part) - 1)
            
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            pdf_writer = PdfWriter()
            
            total_pages = len(pdf_reader.pages)
            
            for i in range(total_pages):
                if i not in pages:
                    pdf_writer.add_page(pdf_reader.pages[i])
            
            output = io.BytesIO()
            pdf_writer.write(output)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Remove pages error: {str(e)}")
    
    @staticmethod
    def merge_pdfs(pdf_bytes_list: list) -> bytes:
        """Merge multiple PDFs into one"""
        try:
            pdf_writer = PdfWriter()
            
            for pdf_bytes in pdf_bytes_list:
                pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            
            output = io.BytesIO()
            pdf_writer.write(output)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Merge error: {str(e)}")
    
    @staticmethod
    def images_to_pdf(image_bytes_list: list) -> bytes:
        """Convert multiple images to a single PDF"""
        temp_files = []
        try:
            # Save images temporarily
            for i, img_bytes in enumerate(image_bytes_list):
                temp_path = f"temp_img_{i}.jpg"
                with Image.open(io.BytesIO(img_bytes)) as im:
                    if im.mode != "RGB":
                        im = im.convert("RGB")
                    im.save(temp_path, "JPEG")
                temp_files.append(temp_path)
            
            # Convert to PDF
            pdf_bytes = img2pdf.convert(temp_files)
            
            output = io.BytesIO(pdf_bytes)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Images to PDF error: {str(e)}")
        finally:
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)
    
    @staticmethod
    def pdf_to_word(pdf_bytes: bytes) -> bytes:
        """Convert PDF to Word document"""
        try:
            temp_pdf = "temp.pdf"
            with open(temp_pdf, "wb") as f:
                f.write(pdf_bytes)
            
            temp_docx = "temp.docx"
            
            cv = Converter(temp_pdf)
            cv.convert(temp_docx)
            cv.close()
            
            with open(temp_docx, "rb") as f:
                docx_bytes = f.read()
            
            os.remove(temp_pdf)
            os.remove(temp_docx)
            
            return docx_bytes
            
        except Exception as e:
            raise Exception(f"PDF to Word error: {str(e)}")