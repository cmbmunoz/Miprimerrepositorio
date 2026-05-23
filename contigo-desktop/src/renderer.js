// Navigation
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => {
    const target = item.dataset.section

    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'))
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'))

    item.classList.add('active')
    document.getElementById(target).classList.add('active')
  })
})

// Populate settings from preload bridge
if (window.contigo) {
  document.getElementById('electron-version').textContent = window.contigo.version()
  document.getElementById('platform').textContent = window.contigo.platform()
}
