from src.html_convert_office.pdf2pptx import ensure_lib_exists
from src.html_convert_office.html2pdf import ensure_playwright_installed
from src.repository.db_utils import init_db

ensure_playwright_installed()
ensure_lib_exists()
init_db()
