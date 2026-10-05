<template>
  <div class="page add">
    <div class="add-head">
      <h1 class="display">Add to the library</h1>
      <RouterLink to="/" class="icon-btn" aria-label="Close"><Icon name="close" :stroke="2.4" /></RouterLink>
    </div>

    <h2 class="section-label">What is it?</h2>
    <div role="radiogroup" aria-label="Type">
      <button v-for="t in types" :key="t.id" class="choice" role="radio" :aria-checked="kind === t.id ? 'true' : 'false'" :disabled="uploading" @click="setKind(t.id)">
        <span class="badge"><Icon :name="t.icon" :size="20" /></span>
        <span class="grow"><span class="title">{{ t.label }}</span><span class="sub">{{ t.hint }}</span></span>
      </button>
    </div>

    <h2 class="section-label">Audio</h2>
    <template v-if="kind === 'song'">
      <label class="dropzone">
        <Icon name="music" />
        <span>{{ songFile ? songFile.name : 'Choose an audio file (.mp3 or .m4a)' }}</span>
        <input class="sr-only" type="file" accept=".mp3,.m4a,audio/mpeg,audio/mp4" :disabled="uploading" @change="onSongFile" />
      </label>
    </template>
    <template v-else>
      <label class="dropzone">
        <Icon name="folder" />
        <span>{{ chapters.length ? `${chapters.length} ${kind === 'album' ? 'tracks' : 'chapters'} chosen · change` : `Choose the ${kind === 'album' ? 'album' : 'story'}’s folder` }}</span>
        <input class="sr-only" type="file" webkitdirectory multiple :disabled="uploading" @change="onFolder" />
      </label>
      <label class="btn btn-ghost btn-block or-files">
        or pick the files instead
        <input class="sr-only" type="file" multiple accept=".mp3,.m4a,audio/mpeg,audio/mp4" :disabled="uploading" @change="onFolder" />
      </label>
      <template v-if="chapters.length">
        <button class="btn btn-ghost btn-block" :aria-expanded="String(editNames)" @click="editNames = !editNames">
          {{ editNames ? 'Hide' : 'Check' }} {{ kind === 'album' ? 'track' : 'chapter' }} names
        </button>
        <ol v-if="editNames" class="ch-edit">
          <li v-for="(ch, i) in chapters" :key="i">
            <span>{{ i + 1 }}</span>
            <input v-model="ch.name" class="input" type="text" :aria-label="`Name of ${kind === 'album' ? 'track' : 'chapter'} ${i + 1}`" />
          </li>
        </ol>
      </template>
    </template>

    <label class="field add-gap">
      <span>Name</span>
      <input v-model="name" class="input" type="text" @input="nameTouched = true" :placeholder="kind === 'story' ? 'Story name' : kind === 'album' ? 'Album name' : 'Song name'" :disabled="uploading" />
    </label>

    <h2 class="section-label">Cover <span class="opt">(optional)</span></h2>
    <div class="cover-row">
      <img v-if="coverPreview" :src="coverPreview" alt="Chosen cover" class="cover-preview" />
      <label class="btn btn-soft">
        <Icon name="camera" :size="20" /> Take photo
        <input class="sr-only" type="file" accept="image/*" capture="environment" :disabled="uploading" @change="onCover" />
      </label>
      <label class="btn btn-soft">
        <Icon name="image" :size="20" /> Choose image
        <input class="sr-only" type="file" accept="image/*" :disabled="uploading" @change="onCover" />
      </label>
    </div>

    <div v-if="uploading" class="card up-progress" role="status">
      <span>Uploading… {{ Math.round(progress * 100) }}%</span>
      <div class="bar"><span :style="{ width: Math.round(progress * 100) + '%' }"></span></div>
      <span class="muted">Keep this screen open until it finishes.</span>
    </div>

    <div class="add-actions">
      <button class="btn btn-primary btn-lg btn-block" :disabled="!ready || uploading" @click="save(true)">
        <Icon v-if="!store.nfc.hw_error" name="sticker" :size="20" />
        {{ store.nfc.hw_error ? 'Save' : 'Save and write a sticker' }}
      </button>
      <button v-if="!store.nfc.hw_error" class="btn btn-ghost btn-block" :disabled="!ready || uploading" @click="save(false)">Save without a sticker</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { upload } from '../api'
import { store, loadSongs, openWriter, cancelWriting, toast } from '../store'
import Icon from '../components/Icon.vue'

const router = useRouter()
const types = [
  { id: 'story', label: 'Story', hint: 'Chapters, and it remembers where you got to', icon: 'book' },
  { id: 'album', label: 'Album', hint: 'Several songs, played in order', icon: 'disc' },
  { id: 'song', label: 'Song', hint: 'One audio file', icon: 'music' },
]
const kind = ref('story')
const name = ref('')
const nameTouched = ref(false)
const songFile = ref(null)
const chapters = ref([])          // [{ file, name }] in the order the box will store them
const editNames = ref(false)
const cover = ref(null)
const coverPreview = ref('')
const uploading = ref(false)
const progress = ref(0)

const ready = computed(() => name.value.trim() && (kind.value === 'song' ? songFile.value : chapters.value.length))

function setKind(k) {
  kind.value = k
  songFile.value = null
  chapters.value = []
}

// Same rules as werkzeug's secure_filename on the box. The box sorts chapter
// files by this, so sorting the same way keeps chapter names lined up.
function secureName(n) {
  return n.normalize('NFKD').replace(/[^\x00-\x7F]/g, '')
    .replace(/[\/\\]/g, ' ').split(/\s+/).filter(Boolean).join('_')
    .replace(/[^A-Za-z0-9_.-]/g, '').replace(/^[._]+|[._]+$/g, '')
}

function tidy(n) {
  return n.replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim()
    .replace(/\b\w/g, (c) => c.toUpperCase()).replace(/(\w)'S\b/g, "$1's")
}
function chapterName(filename) {
  return tidy(filename.replace(/\.[^.]+$/, '').replace(/^CH\d+[\s\-_]+/i, '')) || filename
}
function bookName(folder) {
  return tidy(folder.replace(/^\d+[\s\-_]+/, '')) || folder
}

function onFolder(e) {
  const files = Array.from(e.target.files || []).filter((f) => /\.(mp3|m4a)$/i.test(f.name))
  e.target.value = ''
  if (!files.length) { toast('No .mp3 or .m4a files found there', 'error'); return }
  files.sort((a, b) => { const x = secureName(a.name), y = secureName(b.name); return x < y ? -1 : x > y ? 1 : 0 })
  chapters.value = files.map((f) => ({ file: f, name: chapterName(f.name) }))
  const folder = files[0].webkitRelativePath?.split('/')[0]
  if (folder && (!nameTouched.value || !name.value)) name.value = bookName(folder)
}

function onSongFile(e) {
  const f = e.target.files?.[0]
  if (!f) return
  songFile.value = f
  if (!name.value) name.value = chapterName(f.name)
}

function onCover(e) {
  const f = e.target.files?.[0]
  if (!f) return
  cover.value = f
  if (coverPreview.value) URL.revokeObjectURL(coverPreview.value)
  coverPreview.value = URL.createObjectURL(f)
}
onUnmounted(() => { if (coverPreview.value) URL.revokeObjectURL(coverPreview.value) })

async function save(withSticker) {
  const fd = new FormData()
  fd.append('type', kind.value === 'story' ? 'audiobook' : kind.value === 'album' ? 'album' : 'track')
  fd.append('name', name.value.trim())
  if (cover.value) fd.append('image', cover.value)
  if (kind.value === 'song') {
    fd.append('file', songFile.value)
  } else {
    fd.append('chapter_names', JSON.stringify(chapters.value.map((c) => c.name.trim() || c.file.name)))
    for (const c of chapters.value) fd.append('files[]', c.file)
  }
  uploading.value = true
  progress.value = 0
  try {
    const { status, data } = await upload('/songs', fd, (p) => { progress.value = p })
    await loadSongs()
    router.push('/')
    if (status === 202) {
      if (withSticker) openWriter(data.id)
      else { await cancelWriting(); toast('Saved. Write a sticker any time from its ⋮ menu.', 'ok') }
    } else {
      toast('Saved', 'ok')
    }
  } catch (e) {
    toast(`Upload failed: ${e.message}`, 'error')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.add-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 0 0 4px; margin-right: -8px; }
.add-head h1 { font-size: 24px; }
.or-files { min-height: 44px; margin-top: 4px; }
.ch-edit { list-style: none; margin: 4px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.ch-edit li { display: flex; align-items: center; gap: 8px; }
.ch-edit li > span { width: 26px; text-align: right; font-weight: 700; color: var(--muted); flex-shrink: 0; }
.ch-edit .input { min-height: 48px; }
.add-gap { margin-top: 14px; }
.opt { text-transform: none; letter-spacing: 0; font-weight: 500; }
.cover-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.cover-row .btn { flex: 1 1 140px; }
.cover-preview { width: 64px; height: 64px; border-radius: 14px; object-fit: cover; }
.up-progress { margin-top: 16px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; font-weight: 700; }
.up-progress .bar { height: 8px; }
.up-progress .muted { font-size: 13px; font-weight: 500; }
.add-actions { margin-top: 20px; display: flex; flex-direction: column; gap: 6px; }
</style>
