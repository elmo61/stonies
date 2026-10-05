// While any sheet or overlay is open, stop the page behind it from scrolling.
// Otherwise a scroll inside a sheet "leaks" to the page, which makes mobile
// browsers show/hide their address bar and the sheet jumps around.
let count = 0

export function lockScroll() {
  count += 1
  document.documentElement.classList.add('no-scroll')
}

export function unlockScroll() {
  count = Math.max(0, count - 1)
  if (count === 0) document.documentElement.classList.remove('no-scroll')
}
