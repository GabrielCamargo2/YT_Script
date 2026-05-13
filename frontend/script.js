const { shell } = require("electron");
const path = require("path");
const os = require("os");

document.addEventListener("DOMContentLoaded", () => {
  // API de comunicação com o backend
  const API = {
    URL_BASE: "http://127.0.0.1:5000",

    async request(endpoint, method = "GET", body = null) {
      try {
        const options = {
          method,
          headers: { "Content-Type": "application/json" },
        };
        if (body) options.body = JSON.stringify(body);

        const response = await fetch(`${this.URL_BASE}${endpoint}`, options);
        return await response.json();
      } catch (error) {
        console.error(`Erro na API (${endpoint}):`, error);
        throw error;
      }
    },

    checkFFmpeg: () => API.request("/check_ffmpeg"),
    setupFFmpeg: () => API.request("/setup_ffmpeg", "POST"),
    checkResolucoes: (link) =>
      API.request("/check_resolutions", "POST", { link }),
    download: (link, format) =>
      API.request("/download", "POST", { link, format }),
    pegaProgresso: () => API.request("/progress"),
  };

  // coloquei todas os componentes e funções de manipulação da UI aqui
  const UI = {
    // alias UI = User Interface
    elements: {
      linkInput: document.getElementById("link-input"),
      formatSelect: document.getElementById("format-select"),
      btnDownload: document.getElementById("download-button"),
      statusMsg: document.getElementById("status-message"),
      progressBar: document.getElementById("progress-bar"),
      progressContainer: document.getElementById("progress-container"),
      form: document.getElementById("download-form"),
    },

    definirStatus(message, type = "info") {
      // informa sucesso ou erro
      this.elements.statusMsg.textContent = message;
      this.elements.statusMsg.className = `status-message ${type}`;
    },

    bloqueardor(isLocked) {
      // trava ou libera a tela
      this.elements.linkInput.disabled = isLocked;
      this.elements.formatSelect.disabled = isLocked;
      this.elements.btnDownload.disabled = isLocked;
    },

    mostrarProgresso(show) {
      // mostra barrinha progresso
      this.elements.progressContainer.style.display = show ? "block" : "none";
      if (!show) {
        this.elements.progressBar.style.width = "0%";
        this.elements.progressBar.innerText = "0%";
      }
    },

    atualizaProgresso(percent, message) {
      // atualiza barrinha progresso
      this.elements.progressBar.style.width = `${percent}%`;
      this.elements.progressBar.innerText = `${percent}%`;
      document.getElementById("progress-message").innerText = message;
    },

    listaResolucoes(resolutions) {
      //autoexplicativo
      const select = this.elements.formatSelect;
      select.innerHTML =
        '<option value="" disabled selected>Selecione uma opção</option>';
      select.innerHTML += '<option value="mp3">Áudio (MP3)</option>';

      resolutions.forEach((res) => {
        select.innerHTML += `<option value="${res}">Vídeo (${res})</option>`;
      });
      select.disabled = false;
    },

    resetaBotaoSelect(msg = "Aguardando Link...") {
      this.elements.formatSelect.innerHTML = `<option value="" disabled selected>${msg}</option>`;
      this.elements.formatSelect.disabled = true;
      this.elements.btnDownload.disabled = true;

      // ADICIONE ESTAS DUAS LINHAS:
      this.mostrarProgresso(false);
      document.getElementById("open-downloads-button").style.display = "none";
    },
  };

  // logica do negocio
  function monitorarProgresso(onComplete) {
    UI.mostrarProgresso(true);

    const interval = setInterval(async () => {
      // Monitora o progresso (serve tanto para setup quanto download (eu acho))
      try {
        const data = await API.pegaProgresso();
        UI.atualizaProgresso(data.percent, data.message);

        if (data.status === "downloading" || data.status === "processing") {
          if (data.message) UI.definirStatus(data.message, "highlight");
        }

        if (data.status === "complete") {
          // Processo deu certo
          clearInterval(interval);
          onComplete(true, data);
        }

        if (data.status === "error") {
          //  processo deu erro
          clearInterval(interval);
          UI.definirStatus(`Erro: ${data.message}`, "error");
          UI.mostrarProgresso(false);
          UI.bloqueardor(false);
          onComplete(false, data);
        }
      } catch (error) {
        clearInterval(interval);
        UI.definirStatus("Perda de conexão com o servidor.", "error");
        UI.bloqueardor(false);
        onComplete(false, { message: "Perda de conexão" });
      }
    }, 500);
  }

  // Verifica e Instala FFmpeg se necessário
  async function garantirSistemaPronto() {
    try {
      UI.definirStatus("Verificando sistema...", "info");
      const check = await API.checkFFmpeg();

      if (check.exists) return true;

      // Se não existe, inicia download
      UI.definirStatus(
        "FFmpeg não encontrado. Baixando componentes...",
        "highlight",
      );
      await API.setupFFmpeg();

      return new Promise((resolve) => {
        monitorarProgresso((success) => {
          if (success) {
            UI.definirStatus("Sistema configurado com sucesso!", "success");
            resolve(true);
          } else {
            UI.definirStatus("Falha ao configurar o FFmpeg.", "error");
            resolve(false);
          }
        });
      });
    } catch (error) {
      UI.definirStatus(
        "Erro ao verificar sistema. O servidor está ativo?",
        "error",
      );
      return false;
    }
  }

  // Fluxo principal de download
  async function processaDownload(e) {
    e.preventDefault();
    UI.bloqueardor(true);
    const link = UI.elements.linkInput.value.trim();
    const format = UI.elements.formatSelect.value;

    // Garante que o FFmpeg existe (baixa se precisar) (mochi bundao)
    const systemOk = await garantirSistemaPronto();
    if (!systemOk) {
      UI.bloqueardor(false);
      return;
    }

    // Inicia o Download do Vídeo
    try {
      UI.definirStatus(`Iniciando download (${format})...`, "highlight");

      monitorarProgresso((success, data) => {
        if (success) {
          UI.definirStatus(`Sucesso! Salvo em Downloads.`, "success");

          document.getElementById("open-downloads-button").style.display =
            "inline-block";
        }
        UI.bloqueardor(false);
      });

      const response = await API.download(link, format);

      if (response.status !== "success") {
        throw new Error(response.message);
      }
    } catch (error) {
      UI.definirStatus(`Erro ao iniciar: ${error.message || error}`, "error");
      UI.bloqueardor(false);
    }
  }

  // Carregar Resoluções ao digitar/colar
  async function verificarLink() {
    const link = UI.elements.linkInput.value.trim();

    if (link.length < 10 || !link.includes("youtu")) {
      return UI.resetaBotaoSelect("Cole o link primeiro");
    }

    UI.resetaBotaoSelect("Buscando resoluções...");
    UI.definirStatus("Analisando link...", "highlight");

    try {
      const data = await API.checkResolucoes(link);
      if (data.status === "success") {
        UI.listaResolucoes(data.resolutions);
        UI.definirStatus("Selecione o formato e clique em Baixar.", "success"); // CORRIGIDO: 'sucess' -> 'success'
      } else {
        UI.definirStatus("Link inválido ou privado.", "error");
        UI.resetaBotaoSelect("Erro no link");
      }
    } catch (error) {
      // Ignora erro de digitação rápida, só loga
      console.log("Check ignorado ou falhou");
    }
  }

  // isso serve pra nao chamar a função toda hora que o usuario digita uma letra (F memoria se acontecese)

  function evitaFlood(func, wait) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  function abrirPastaDownloads() {
    const downloadsPath = path.join(os.homedir(), "Downloads", "YT_Downloads");
    shell.openPath(downloadsPath);
  }

  UI.elements.form.addEventListener("submit", processaDownload);

  // Abre pasta de Downloads
  document.addEventListener("click", (e) => {
    if (e.target.id === "open-downloads-button") {
      abrirPastaDownloads();
    }
  });

  UI.elements.linkInput.addEventListener(
    "input",
    evitaFlood(verificarLink, 800),
  );
  UI.elements.linkInput.addEventListener("paste", () =>
    setTimeout(verificarLink, 100),
  );

  UI.elements.formatSelect.addEventListener("change", () => {
    if (UI.elements.formatSelect.value) {
      UI.elements.btnDownload.disabled = false;
      UI.elements.btnDownload.textContent = `Baixar ${UI.elements.formatSelect.options[UI.elements.formatSelect.selectedIndex].text}`;
    }
  });
});
