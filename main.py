import os
import logging
import io
import traceback
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pdf_utils import PDFTool

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ HELPERS ============
def show_main_menu():
    """Show main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("💧 Watermark", callback_data="watermark"),
            InlineKeyboardButton("❌ Remove Pages", callback_data="removepages")
        ],
        [
            InlineKeyboardButton("📚 Merge PDFs", callback_data="merge"),
            InlineKeyboardButton("🖼️ Images to PDF", callback_data="imagestopdf")
        ],
        [
            InlineKeyboardButton("📝 PDF to Word", callback_data="pdftoword")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ COMMAND HANDLERS ============
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
📄 **PDF Tool Bot**

I can help you with various PDF operations!

**Available Features:**

💧 **Watermark** - Add watermark to PDF
❌ **Remove Pages** - Remove specific pages (e.g., 6-9)
📚 **Merge PDFs** - Combine multiple PDFs
🖼️ **Images to PDF** - Convert images to PDF
📝 **PDF to Word** - Convert PDF to Word

**How to use:**
1. Select a feature from the menu below
2. Follow the instructions
3. Get your processed file! 🎉

Select an option below! 👇
"""
    reply_markup = show_main_menu()
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ============ FEATURE HANDLERS ============
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from menu"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    context.user_data['operation'] = data
    
    if data == "watermark":
        await query.edit_message_text(
            "💧 **Watermark**\n\n"
            "Send me the PDF file and then the watermark text.\n\n"
            "**Usage:**\n"
            "1. Send a PDF file\n"
            "2. Send the watermark text (e.g., 'SAMPLE', 'CONFIDENTIAL')\n"
            "3. I'll add the watermark!",
            parse_mode='Markdown'
        )
    
    elif data == "removepages":
        await query.edit_message_text(
            "❌ **Remove Pages**\n\n"
            "Send me the PDF file and then the pages to remove.\n\n"
            "**Usage:**\n"
            "1. Send a PDF file\n"
            "2. Send page numbers (e.g., '6-9' or '1,3,5' or '2-4,7')\n"
            "3. I'll remove those pages!",
            parse_mode='Markdown'
        )
    
    elif data == "merge":
        await query.edit_message_text(
            "📚 **Merge PDFs**\n\n"
            "Send me up to 3 PDF files to merge.\n\n"
            "**Usage:**\n"
            "1. Send PDF 1\n"
            "2. Send PDF 2\n"
            "3. Send PDF 3 (optional)\n"
            "4. Send /done when finished\n"
            "5. I'll merge them!",
            parse_mode='Markdown'
        )
        context.user_data['pdfs'] = []
    
    elif data == "imagestopdf":
        await query.edit_message_text(
            "🖼️ **Images to PDF**\n\n"
            "Send me up to 10 images to convert to PDF.\n\n"
            "**Usage:**\n"
            "1. Send images one by one\n"
            "2. Send /done when finished\n"
            "3. I'll convert them to PDF!",
            parse_mode='Markdown'
        )
        context.user_data['images'] = []
    
    elif data == "pdftoword":
        await query.edit_message_text(
            "📝 **PDF to Word**\n\n"
            "Send me a PDF file to convert to Word.\n\n"
            "**Usage:**\n"
            "1. Send a PDF file\n"
            "2. I'll convert it to Word (.docx)!",
            parse_mode='Markdown'
        )
    
    elif data == "back_to_menu":
        await query.edit_message_text(
            "📄 **PDF Tool Bot**\n\n"
            "Select an option below! 👇",
            reply_markup=show_main_menu(),
            parse_mode='Markdown'
        )

# ============ FILE HANDLERS ============
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF files"""
    document = update.message.document
    operation = context.user_data.get('operation', '')
    
    if not operation:
        await update.message.reply_text(
            "⚠️ Please select an operation first using /start",
            reply_markup=show_main_menu()
        )
        return
    
    # Check if it's a PDF for operations that require PDF
    if operation in ["watermark", "removepages", "pdftoword"]:
        if not document.mime_type or document.mime_type != "application/pdf":
            await update.message.reply_text("⚠️ Please send a PDF file!")
            return
    
    # Download the file
    file = await document.get_file()
    file_bytes = await file.download_as_bytearray()
    
    context.user_data['current_pdf'] = bytes(file_bytes)
    context.user_data['current_file_name'] = document.file_name
    
    if operation == "watermark":
        await update.message.reply_text(
            "✅ PDF received!\n\n"
            "Now send the watermark text:\n"
            "(e.g., 'SAMPLE', 'CONFIDENTIAL', '© 2024')\n\n"
            "Or send /cancel to cancel."
        )
        context.user_data['awaiting_watermark_text'] = True
    
    elif operation == "removepages":
        await update.message.reply_text(
            "✅ PDF received!\n\n"
            "Now send the pages to remove:\n"
            "- Single page: `5`\n"
            "- Range: `6-9`\n"
            "- Multiple: `2-4,7`\n\n"
            "Or send /cancel to cancel.",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_pages'] = True
    
    elif operation == "pdftoword":
        await update.message.reply_text("⏳ Converting PDF to Word... Please wait...")
        try:
            result = PDFTool.pdf_to_word(file_bytes)
            await update.message.reply_document(
                document=io.BytesIO(result),
                filename=document.file_name.replace('.pdf', '.docx'),
                caption="✅ **PDF to Word conversion successful!** 🎉"
            )
        except Exception as e:
            logger.error("PDF to Word failed:\n%s", traceback.format_exc())
            await update.message.reply_text(f"❌ Error: {repr(e)}")
    
    elif operation == "merge":
        if 'pdfs' not in context.user_data:
            context.user_data['pdfs'] = []
        context.user_data['pdfs'].append(bytes(file_bytes))
        await update.message.reply_text(
            f"✅ PDF received! ({len(context.user_data['pdfs'])}/3)\n"
            "Send more PDFs or type /done to merge."
        )
    
    elif operation == "imagestopdf":
        # Check if it's an image
        if not document.mime_type or not document.mime_type.startswith('image/'):
            await update.message.reply_text("⚠️ Please send an image file (JPG/PNG)!")
            return
        
        if 'images' not in context.user_data:
            context.user_data['images'] = []
        context.user_data['images'].append(bytes(file_bytes))
        await update.message.reply_text(
            f"✅ Image received! ({len(context.user_data['images'])}/10)\n"
            "Send more images or type /done to create PDF."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle images sent as compressed photos (not as files/documents)"""
    operation = context.user_data.get('operation', '')

    if operation != "imagestopdf":
        await update.message.reply_text(
            "⚠️ Please select an operation first using /start",
            reply_markup=show_main_menu()
        )
        return

    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    if 'images' not in context.user_data:
        context.user_data['images'] = []
    context.user_data['images'].append(bytes(file_bytes))

    await update.message.reply_text(
        f"✅ Image received! ({len(context.user_data['images'])}/10)\n"
        "Send more images or type /done to create PDF."
    )

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done command - finishes merge or images-to-pdf flow"""
    operation = context.user_data.get('operation', '')

    if operation == "merge":
        pdfs = context.user_data.get('pdfs', [])
        if len(pdfs) < 2:
            await update.message.reply_text("⚠️ Need at least 2 PDFs to merge!")
            return

        await update.message.reply_text("⏳ Merging PDFs... Please wait...")
        try:
            result = PDFTool.merge_pdfs(pdfs)
            await update.message.reply_document(
                document=io.BytesIO(result),
                filename="merged.pdf",
                caption="✅ **PDFs merged successfully!** 🎉"
            )
            context.user_data.clear()
        except Exception as e:
            logger.error("Merge failed:\n%s", traceback.format_exc())
            await update.message.reply_text(f"❌ Error: {repr(e)}")
        return

    elif operation == "imagestopdf":
        images = context.user_data.get('images', [])
        if len(images) < 1:
            await update.message.reply_text("⚠️ Need at least 1 image!")
            return

        await update.message.reply_text("⏳ Converting images to PDF... Please wait...")
        try:
            result = PDFTool.images_to_pdf(images)
            await update.message.reply_document(
                document=io.BytesIO(result),
                filename="images.pdf",
                caption="✅ **Images converted to PDF successfully!** 🎉"
            )
            context.user_data.clear()
        except Exception as e:
            logger.error("Images to PDF failed:\n%s", traceback.format_exc())
            await update.message.reply_text(f"❌ Error: {repr(e)}")
        return

    else:
        await update.message.reply_text(
            "❌ No operation in progress!\n"
            "Use /start to select an operation.",
            reply_markup=show_main_menu()
        )
        return

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operation cancelled!",
        reply_markup=show_main_menu()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for watermark text and page numbers"""
    text = update.message.text.strip()
    
    # ============ WATERMARK TEXT ============
    if context.user_data.get('awaiting_watermark_text'):
        try:
            pdf_bytes = context.user_data.get('current_pdf')
            if not pdf_bytes:
                await update.message.reply_text("❌ No PDF found! Please send a PDF first.")
                return
            
            await update.message.reply_text(
                f"⏳ Adding watermark '{text}'... Please wait..."
            )
            result = PDFTool.add_watermark(pdf_bytes, text)
            await update.message.reply_document(
                document=io.BytesIO(result),
                filename=context.user_data.get('current_file_name', 'watermarked.pdf'),
                caption=f"✅ **Watermark added successfully!** 🎉\n\n"
                       f"📝 Watermark: `{text}`"
            )
            context.user_data.clear()
            
        except Exception as e:
            logger.error("Watermark failed:\n%s", traceback.format_exc())
            await update.message.reply_text(f"❌ Error: {repr(e)}")
        
        context.user_data['awaiting_watermark_text'] = False
        return
    
    # ============ REMOVE PAGES ============
    if context.user_data.get('awaiting_pages'):
        try:
            pdf_bytes = context.user_data.get('current_pdf')
            if not pdf_bytes:
                await update.message.reply_text("❌ No PDF found! Please send a PDF first.")
                return
            
            await update.message.reply_text(
                f"⏳ Removing pages '{text}'... Please wait..."
            )
            result = PDFTool.remove_pages(pdf_bytes, text)
            await update.message.reply_document(
                document=io.BytesIO(result),
                filename=context.user_data.get('current_file_name', 'pages_removed.pdf'),
                caption=f"✅ **Pages removed successfully!** 🎉\n\n"
                       f"🗑️ Removed pages: `{text}`"
            )
            context.user_data.clear()
            
        except Exception as e:
            logger.error("Remove pages failed:\n%s", traceback.format_exc())
            await update.message.reply_text(f"❌ Error: {repr(e)}")
        
        context.user_data['awaiting_pages'] = False
        return
    
    # ============ UNKNOWN TEXT ============
    await update.message.reply_text(
        "⚠️ I didn't understand that.\n\n"
        "Use /start to see the menu.",
        reply_markup=show_main_menu()
    )

# ============ MAIN FUNCTION ============
def main():
    print("\n" + "="*50)
    print("📄 Starting PDF Tool Bot...")
    
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Bot is running!")
    print("📚 Features: Watermark | Remove Pages | Merge | Images to PDF | PDF to Word")
    print("⏹️ Press CTRL+C to stop")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()