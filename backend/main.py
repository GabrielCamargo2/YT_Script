import os
import subprocess
import time
import sys
import platform
from pytubefix import YouTube
from pytubefix.cli import on_progress
from mutagen.id3 import ID3, TIT2, TPE1, TALB
from ffmpeg_download import Verificar_FFmpeg, Baixar_FFmpeg 

try:

  if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding = 'utf-8')

except AttributeError:

  pass

except Exception as error:
  print(f"Aviso: Nao foi possivel configurar o stdout para UTF-8. Erro: {error}")

if getattr(sys, 'frozen', False):

  base_dir = os.path.dirname(sys.executable)

else:

  base_dir = os.path.dirname(os.path.abspath(__file__))


if platform.system() == "Windows":
    path_ffmpeg = os.path.join(base_dir, 'ffmpeg', 'ffmpeg.exe')
else:
    path_ffmpeg = "ffmpeg"

home_dir = os.path.expanduser('~')

dir_save = os.path.join(home_dir, 'Downloads', 'YT_Downloads')

try:

  os.makedirs(dir_save, exist_ok = True)

except Exception as error:
  print(f"ERRO FATAL: Nao foi possivel criar ou acessar o diretorio de destino: {dir_save}. Detalhes: {error}")

def get_available_resolutions(link_url:str):

  try:
    yt = YouTube(link_url)

    streams = yt.streams.filter(file_extension = 'mp4', res = True, progressive = False).order_by('resolution').desc()

    resolutions = set()

    for stream in streams:
      if stream.resolution:
        resolutions.add(stream.resolution)

    return sorted(list(resolutions), key = lambda x: int(x.replace('p', '')), reverse = True)

  except Exception as error:

    print(f"ERRO ao obter resolucoes para o link: {link_url}: {error}")

    return[]

def iniciar_download(link_url: str, formato: str, progress_callback, overwrite_flag: bool = False):

  def pytube_progress_wrapper(stream, chunk, bytes_remaining):

    filesize = stream.filesize
    bytes_received = filesize - bytes_remaining
    percent = (bytes_received / filesize) * 100
    
    progress_callback('downloading', int (percent), 'Baixando stream...')

    #on_progress(stream, chunk, bytes_remaining)

  selected_option = formato.lower()

  timestamp = int(time.time())

  temp_video = f"video_temp{timestamp}.mp4"
  temp_audio = f"audio_temp{timestamp}.mp3"

  path_temp_video = os.path.join(dir_save, temp_video)
  path_temp_audio = os.path.join(dir_save, temp_audio)

  if not link_url:
    progress_callback('error', 0, 'Link do Youtube ausente.')
    return{"status": "error", "message": "Link do Youtube ausente."}

  try:
    yt = YouTube(link_url, on_progress_callback = pytube_progress_wrapper)

  except Exception as error:
    progress_callback('error', 0, f'Erro ao inicializar o video: {error}')
    return{"status": "error", "message": f"Erro ao inicializar o video: {error}"}

  forbidden_chars = r'<>:"\/|?*'
  cleaned_title = yt.title

  for char in forbidden_chars:
    cleaned_title = cleaned_title.replace(char, '')

  cleaned_title_ascii = "".join([
    c if (c.isalnum() or c in (' ', '.', '_', '-')) and ord(c) < 128 else '_'
    for c in cleaned_title
  ])

  cleaned_title_ascii = cleaned_title_ascii.replace('\n', ' ').replace('\r', ' ').strip()

  final_base_name = '_'.join(cleaned_title_ascii.split())
  final_base_name = final_base_name.strip(' _-')
  final_base_name = final_base_name[:100]

  arquivo_final_mp4 = f"{final_base_name}.mp4"

  path_arquivo_final_mp4 = os.path.join(dir_save, arquivo_final_mp4)

  arquivo_final_mp3 = f"{final_base_name}.mp3"
  path_arquivo_final_mp3 = os.path.join(dir_save, arquivo_final_mp3)

  audio_stream = yt.streams.get_audio_only()
  video_stream = None

  if selected_option ==  'mp3':
    path_arquivo_final = path_arquivo_final_mp3

  else:
    path_arquivo_final = path_arquivo_final_mp4

  if os.path.exists(path_arquivo_final) and not overwrite_flag:
    nome_arquivo = os.path.basename(path_arquivo_final)
    progress_callback('error', 0, f"Download cancelado. O arquivo '{nome_arquivo}' ja existe.")
    return{
      "status": "error",
      "message": f"O download foi cancelado porque o arquivo '{nome_arquivo} ja existe no diretorio de destino."
    }
  
  if selected_option != 'mp3':
    video_stream = yt.streams.filter(
      res = selected_option,
      progressive = False,
    ).first()

    if not video_stream:
      return{"status": "error", "message": f"Nenhuma stream de video encontrada para a resolucao {selected_option}."}
    
  if not audio_stream:
    return{"status": "error", "message": "Nao foi possivel encontrar o stream de audio."}

  try:

    if selected_option == 'mp3':
      print(f"Baixando Audio: {audio_stream.abr}...")

      audio_stream.download(output_path = dir_save, filename = temp_audio)

      print("Iniciando conversao para MP3...")

      ffmpeg_conversion_command = [
        path_ffmpeg,
        '-i', path_temp_audio,
        '-vn',
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        path_arquivo_final_mp3
      ]
      subprocess.run(ffmpeg_conversion_command, check = True, capture_output = True)

      print("Injetando metadados...")
      progress_callback('processing', 95, 'Injetando metadados...')

      audio_file = ID3(path_arquivo_final_mp3)
      audio_file['TIT2'] = TIT2(encoding = 3, text = yt.title)
      audio_file['TPE1'] = TPE1(encoding = 3, text = yt.author)
      audio_file['TALB'] = TALB(encoding = 3, text = "Youtube Downloads")
      audio_file.save()

      progress_callback('complete', 100, f"Download de Áudio Concluido.")
      return{"status": "success",
            "message": f"Download concluido. {arquivo_final_mp3}",
            "filepath": path_arquivo_final_mp3}

    else:
      print(f"\nBaixando Video({video_stream.resolution})")

      video_stream.download(output_path = dir_save, filename = temp_video)
      audio_stream.download(output_path = dir_save, filename = temp_audio)

      print("Iniciando a combinacao dos arquivos FFmpeg...")
      progress_callback('processing', 90, 'Combinando video e audio (FFmpeg)...')

      ffmpeg_command = [
        path_ffmpeg,
        '-i', path_temp_video,
        '-i', path_temp_audio,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        path_arquivo_final_mp4
      ]
      subprocess.run(ffmpeg_command, check = True, capture_output = True)

      progress_callback('complete', 100, f"Download de Video concluido.")
      return{"status": "success",
            "message": f"Download concluido: {arquivo_final_mp4}",
            "filepath": path_arquivo_final_mp4}

  except FileNotFoundError:
    return{"status": "error", "message": f"ERRO FATAL: FFmpeg nao foi encontrado no caminho especificado."}

  except subprocess.CalledProcessError as error:
    return{"status": "error", "message": f"ERRO FFmpeg: {error.stderr.decode()}"}

  except Exception as error:
    progress_callback('error', 0, f"Ocorreu um erro inesperado: {str(error)}")
    return{"status": "error", "message": f"Ocorreu um erro inesperado: {str(error)}"}

  finally:
    temp_files_persisted = True

    if os.path.exists(path_temp_video):

      try:
        os.remove(path_temp_video)

      except Exception:
        temp_files_persisted = True

    if os.path.exists(path_temp_audio):

      try:
        os.remove(path_temp_audio)

      except Exception:
        temp_files_persisted = True

    if temp_files_persisted:
      print(f"\nAVISO (Servidor): Arquivos temporarios persistiram em {dir_save}.")

    else:
      print(f"INFO (Servidor): Arquivos temporarios removidos.")