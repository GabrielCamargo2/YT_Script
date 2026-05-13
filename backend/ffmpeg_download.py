import os
import urllib.request
import zipfile
import shutil
import platform

def Verificar_FFmpeg(path_ffmpeg):
    if platform.system() != "Windows":
        return shutil.which("ffmpeg") is not None
    return os.path.exists(path_ffmpeg)

def Baixar_FFmpeg(base_dir, callback_status):
    if platform.system() != "Windows":
        callback_status('error', 0, "No Linux, instale no terminal: sudo apt install ffmpeg")
        return False

    pasta_ffmpeg = os.path.join(base_dir, 'ffmpeg')
    path_zip = os.path.join(pasta_ffmpeg, 'ffmpeg_temp.zip')
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    os.makedirs(pasta_ffmpeg, exist_ok=True)

    try:
        callback_status('processing', 10, "Baixando motor (pode demorar alguns minutos)...")
        urllib.request.urlretrieve(url, path_zip)
        
        callback_status('processing', 80, "Extraindo arquivos...")
        with zipfile.ZipFile(path_zip, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith("ffmpeg.exe"):
                    with zip_ref.open(file) as source, open(os.path.join(pasta_ffmpeg, "ffmpeg.exe"), "wb") as target:
                        shutil.copyfileobj(source, target)
        
        os.remove(path_zip)
        callback_status('complete', 100, "Sistema pronto!")
        return True
    except Exception as e:
        callback_status('error', 0, f"ERRO: {e}")
        return False