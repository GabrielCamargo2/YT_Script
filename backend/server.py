from flask import Flask, request, jsonify
from main import iniciar_download, get_available_resolutions, base_dir, path_ffmpeg
import os
import threading

app = Flask(__name__, static_folder = '.', static_url_path = '')

download_progress = {'status': 'idle', 'percent': 0, 'message': 'Pronto'}

def update_progress_state(status, percent, message):
    global download_progress
    download_progress['status'] = status
    download_progress['percent'] = percent
    download_progress['message'] = message

@app.route('/')
def serve_index():

    try:
        return app.send_static_file('index.html')
    
    except Exception as error:
        return f"Erro ao servir os arquivos do sistema. Verifique se o index e demais arquivos existem. Erro: {error}", 500

@app.route('/download', methods = ['POST'])
def handle_download():
    
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type deve ser application/json"}), 415

    data = request.get_json()
    link = data.get('link')
    format_option = data.get('format')
    overwrite_flag = data.get('overwrite', False)

    if not link or not format_option:
        update_progress_state('error', 0, "Campos 'link' ou 'formato' ausentes.")
        return jsonify({"status": "error", "message": "Campos 'link' ou 'formato' ausentes."}), 400

    print(f"[{os.getpid()}] Requisicao recebida: Link = {link[:30]}..., Formato = {format_option}")

    update_progress_state('downloading', 0, f'Iniciando download de {format_option}')
    resultado = iniciar_download(link, format_option, update_progress_state, overwrite_flag)

    if resultado.get("status") == "success":
        update_progress_state('complete', 100, resultado.get("message"))
        return jsonify(resultado), 200

    else:
        update_progress_state('error', 0, resultado.get("message"))
        return jsonify(resultado), 500

@app.route('/progress', methods = ['GET'])
def get_progress():
    global download_progress
    return jsonify(download_progress), 200

@app.route('/check_ffmpeg', methods=['GET'])
def check_ffmpeg_status():
    from ffmpeg_download import Verificar_FFmpeg
    exists = Verificar_FFmpeg(path_ffmpeg) #path_ffmpeg já está definido no main.py
    return jsonify({"exists": exists})

@app.route('/setup_ffmpeg', methods=['POST'])
def setup_ffmpeg():
    from ffmpeg_download import Baixar_FFmpeg
    #Thread para não travar a requisição HTTP
    def run_setup():
        Baixar_FFmpeg(base_dir, update_progress_state)
    
    threading.Thread(target=run_setup).start()
    return jsonify({"status": "started"})
@app.route('/check_resolutions', methods=['POST'])
def check_resolutions():

    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type deve ser application/json'}), 415
    data = request.json
    link = data.get('link')

    if not link:
        return jsonify({'status': 'error', 'message': 'Link nao fornecido'}), 400

    try:
        resolutions = get_available_resolutions(link)

        if not resolutions:
            return jsonify({'statuts': 'error', 'message': 'Nao foi possivel encontrar resolucoes validas para este link.'}), 404
        return jsonify({'status': 'success', 'resolutions': resolutions})

    except Exception as error:
        print(f"ERRO DE PROCESSAMENTO DO LINK: {error}")
        return jsonify({'status': 'error', 'message': f'Erro interno ao processar o link: {str(error)}'}), 500

if __name__ == '__main__':
    print("Servidor Flask rodando em http://127.0.0.1:5000")
    
    app.run(host = '127.0.0.1', port = 5000, debug = False)