// Cover pictures: shrink on the phone, then upload to the box.
// Phone photos and print-quality artwork can be several MB; 600px is plenty
// for the app and for speakers with screens, and quick for a Pi Zero to serve.
import { upload } from './api'
import { toast } from './store'

const MAX_SIDE = 600

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => resolve({ img, url })
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("that image couldn't be opened")) }
    img.src = url
  })
}

// Returns a JPEG no bigger than MAX_SIDE on its longest side (GIFs are left
// alone so animations survive; small JPEGs are sent as they are)
export async function shrinkImage(file, maxSide = MAX_SIDE) {
  if (file.type === 'image/gif') return file
  const { img, url } = await loadImage(file)
  try {
    const scale = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight))
    if (scale === 1 && file.type === 'image/jpeg' && file.size < 300_000) return file
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(img.naturalWidth * scale))
    canvas.height = Math.max(1, Math.round(img.naturalHeight * scale))
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#FFFFFF'                 // transparent PNGs get a white background
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.85))
    return blob ? new File([blob], 'cover.jpg', { type: 'image/jpeg' }) : file
  } finally {
    URL.revokeObjectURL(url)
  }
}

export async function uploadCover(song, file) {
  const small = await shrinkImage(file)
  const fd = new FormData()
  fd.append('image', small, small.name || 'cover.jpg')
  const { data } = await upload(`/songs/${song.id}/image`, fd)
  song.image_url = data.image_url
}

// Open the phone's picker (camera or photos) and set the chosen picture as the
// song's cover. Must be called straight from a tap so the browser allows it.
export function chooseCover(song) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.style.display = 'none'
  document.body.appendChild(input)
  input.addEventListener('cancel', () => input.remove(), { once: true })
  input.addEventListener('change', async () => {
    const file = input.files?.[0]
    input.remove()
    if (!file) return
    toast('Updating the cover…')
    try {
      await uploadCover(song, file)
      toast('Cover updated', 'ok')
    } catch (e) {
      toast(`Couldn't update the cover: ${e.message}`, 'error')
    }
  }, { once: true })
  input.click()
}
