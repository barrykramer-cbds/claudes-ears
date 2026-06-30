export interface ElectronBridge {
  openAudioFile: () => Promise<string | null>;
}

declare global {
  interface Window {
    electron?: ElectronBridge;
  }
}
