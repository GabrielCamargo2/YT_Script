import { app, BrowserWindow } from 'electron'; 
import { spawn } from 'child_process'; //transformei a importacao em uma unica linha
import { join } from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

let mainWindow;
let flaskProcess;


function createWindow() {
    mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        icon: join(__dirname, 'assets', 'icon.ico'), // Garante o ícone
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            webSecurity: false
        }
    });
    
    mainWindow.setMenuBarVisibility(false);

    if (app.isPackaged) {
        
        const htmlPath = join(process.resourcesPath, 'frontend', 'index.html');
        console.log("Tentando carregar (Prod):", htmlPath); //debug
        mainWindow.loadFile(htmlPath);
    } else {
        
        
        const htmlPath = join(__dirname, 'frontend', 'index.html');
        console.log("Tentando carregar (Dev):", htmlPath);
        mainWindow.loadFile(htmlPath);
    }

    // abre um console para mostrar qual o erro caso nao consiga carregar o html
    mainWindow.webContents.on('did-fail-load', () => {
        mainWindow.webContents.openDevTools();
    });
}

function createFlaskProcess() { // Inicia o servidor Flask
    
    const isPackaged = app.isPackaged;
    let backendPath;

    // cria o executavel nos dois sistemas
    const executableName = process.platform === 'win32' ? 'server.exe' : 'server';

    if (isPackaged) {
        
        backendPath = join(process.resourcesPath, 'dist', executableName);
    } else {
       
        backendPath = join(__dirname, 'dist', executableName);
    }

    console.log("Tentando iniciar backend em:", backendPath);

    flaskProcess = spawn(backendPath, [], { stdio: ['ignore', 'pipe', 'pipe'] });

    flaskProcess.stdout.on('data', (data) => {
        console.log(`[PYTHON]: ${data.toString()}`);
    });

    flaskProcess.stderr.on('data', (data) => {
        console.error(`[PYTHON ERRO]: ${data.toString()}`);
    });
    
    flaskProcess.on('error', (err) => {
        console.error('Falha ao iniciar processo Python:', err);
    });
}

app.whenReady().then(() => {
	createFlaskProcess();

	setTimeout(createWindow, 5000);
});

function killFlaskProcess() {
    if (!flaskProcess){
        return;
    }
    const pid = flaskProcess.pid;

    try {
        if (process.platform === 'win32') {
            // mata o processo pelo id do processo
            spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true });
        } 
    } catch (err) {
        console.error('Erro ao pedir para encerrar backend:', err);
    }

    // Verifica se o processo ainda existe e aplica fallback
    setTimeout(() => {
        let alive = true;
        try {
            process.kill(pid, 0);
            alive = true;
        } catch (err) {
            alive = false;
        }

        if (alive) {
            // mata pelo fallback
            //fallbacks sao esses metodos abaixo para matar o processo, ou seja um plano B
            if (process.platform === 'win32') {
                spawn('taskkill', ['/IM', 'server.exe', '/F'], { windowsHide: true });
            } else {
                try { spawn('pkill', ['-f', 'server'], { stdio: 'ignore' }); } catch (e) { /* ignore */ }
            }
        } else {
            console.log('Backend finalizado.');
        }
    }, 1500);

    flaskProcess = null;
}

app.on('before-quit', () => {
    killFlaskProcess();
});

app.on('window-all-closed', () => {
    killFlaskProcess();

    if (process.platform !== 'darwin') {
        app.quit();
    }
});
