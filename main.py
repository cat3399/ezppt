from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.html_convert_office.html2pdf import ensure_playwright_installed
from src.api.projects import router
import uvicorn
from config.logging_config import logger
from src.repository.db_utils import init_db
import shutil

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "data" / "projects"
WEBUI_DIR = BASE_DIR / "webui"
ENV_FILE = BASE_DIR / ".env"
ENV_TEMPLATE_FILE = BASE_DIR / ".env.template"
# 检查并创建 .env 文件
if not ENV_FILE.exists() and ENV_TEMPLATE_FILE.exists():
    shutil.copy(ENV_TEMPLATE_FILE, ENV_FILE)
    logger.warning(".env 文件不存在,已从 .env.template 创建,请手动修改!!!")
elif not ENV_TEMPLATE_FILE.exists():
    logger.error(".env.template 文件不存在，无法自动创建 .env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if PROJECTS_DIR.exists():
    app.mount("/projects", StaticFiles(directory=str(PROJECTS_DIR)), name="projects")

if WEBUI_DIR.exists():
    app.mount("/webui", StaticFiles(directory=str(WEBUI_DIR)), name="webui")
    # 挂载CSS和JS目录到根路径，以便HTML相对路径正确解析
    css_dir = WEBUI_DIR / "css"
    js_dir = WEBUI_DIR / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")


@app.get("/")
async def root():
    """主页 - 项目列表"""
    home_file = WEBUI_DIR / "pages" / "home.html"
    if home_file.exists():
        return FileResponse(str(home_file))
    raise HTTPException(status_code=404, detail="home.html 不存在")


@app.get("/home.html")
async def home_page():
    """项目列表页面"""
    home_file = WEBUI_DIR / "pages" / "home.html"
    if home_file.exists():
        return FileResponse(str(home_file))
    raise HTTPException(status_code=404, detail="home.html 不存在")


@app.get("/preview.html")
async def preview_page():
    """预览页面"""
    preview_file = WEBUI_DIR / "pages" / "preview.html"
    if preview_file.exists():
        return FileResponse(str(preview_file))
    raise HTTPException(status_code=404, detail="preview.html 不存在")


if __name__ == "__main__":
    init_db()
    # ensure_playwright_installed()
    logger.info("Starting server in http://127.0.0.1:8000")
    # 将 app 对象改为导入字符串
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["src"])
