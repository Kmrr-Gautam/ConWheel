APP_NAME = "conWheel"
APP_VERSION = "1.0.0"
ORG_NAME = "conWheel"

CATEGORIES = ["Documents", "Images", "Audio", "Video", "Spreadsheets",
              "Presentations", "Text and data", "Archives"]

# format key -> display category
FORMAT_CATEGORY = {
    "pdf": "Documents", "docx": "Documents", "doc": "Documents", "odt": "Documents",
    "rtf": "Documents",
    "png": "Images", "jpg": "Images", "webp": "Images", "bmp": "Images",
    "tiff": "Images", "gif": "Images", "ico": "Images",
    "mp3": "Audio", "wav": "Audio", "flac": "Audio", "aac": "Audio",
    "m4a": "Audio", "ogg": "Audio", "opus": "Audio",
    "mp4": "Video", "mkv": "Video", "mov": "Video", "avi": "Video", "webm": "Video",
    "xlsx": "Spreadsheets", "xls": "Spreadsheets", "ods": "Spreadsheets",
    "pptx": "Presentations", "ppt": "Presentations", "odp": "Presentations",
    "txt": "Text and data", "md": "Text and data", "html": "Text and data",
    "json": "Text and data", "xml": "Text and data", "csv": "Text and data",
    "tsv": "Text and data",
    "zip": "Archives", "tar": "Archives", "tgz": "Archives", "gz": "Archives",
}

# Formats shown first on the wheel
COMMON_FORMATS = {"pdf", "docx", "png", "jpg", "mp3", "mp4", "xlsx", "csv",
                  "txt", "zip", "wav", "webp", "json"}
