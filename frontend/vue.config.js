const { defineConfig } = require('@vue/cli-service')
const fs = require('fs')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    https: true,
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
      "Cross-Origin-Embedder-Policy": "unsafe-none"
    },
    liveReload: true,
    watchFiles: {
      options: {
        usePolling: true
      }
    },
    allowedHosts: ['aomail.ai', 'jean.aomail.ai', 'augustin.aomail.ai', 'theo.aomail.ai', 'localhost'],
  }
})
