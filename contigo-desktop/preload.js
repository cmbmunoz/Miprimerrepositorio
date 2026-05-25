const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('contigo', {
  version: () => process.versions.electron,
  platform: () => process.platform,
  onMessage: (callback) => ipcRenderer.on('message', (_event, value) => callback(value))
})
