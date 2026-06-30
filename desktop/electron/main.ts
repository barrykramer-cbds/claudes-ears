import { join } from "node:path";
import { type ChildProcess, spawn } from "node:child_process";
import { app, BrowserWindow, dialog, ipcMain } from "electron";

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL;

let sidecar: ChildProcess | null = null;

// Skeleton: the PyInstaller-frozen FastAPI sidecar gets spawned here later
// (resolves the bundled binary, picks a free port, waits for /health). Stubbed for now.
function startSidecar(): void {
  const binary = process.env.CLAUDES_EARS_SIDECAR;
  if (!binary) {
    console.info("[sidecar] not configured — renderer runs on mock data");
    return;
  }
  sidecar = spawn(binary, [], { stdio: "inherit" });
  sidecar.on("exit", (code) => console.info(`[sidecar] exited (${String(code)})`));
}

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1100,
    height: 760,
    backgroundColor: "#0c0d12",
    webPreferences: { preload: join(__dirname, "preload.cjs") },
  });
  if (DEV_SERVER_URL) void win.loadURL(DEV_SERVER_URL);
  else void win.loadFile(join(__dirname, "../dist/index.html"));
}

ipcMain.handle("dialog:openAudioFile", async (): Promise<string | null> => {
  const result = await dialog.showOpenDialog({
    properties: ["openFile"],
    filters: [{ name: "Audio", extensions: ["flac", "wav", "mp3", "m4a", "ogg"] }],
  });
  return result.canceled ? null : (result.filePaths[0] ?? null);
});

void app.whenReady().then(() => {
  startSidecar();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  sidecar?.kill();
  if (process.platform !== "darwin") app.quit();
});
