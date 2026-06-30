import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electron", {
  openAudioFile: (): Promise<string | null> => ipcRenderer.invoke("dialog:openAudioFile"),
});
