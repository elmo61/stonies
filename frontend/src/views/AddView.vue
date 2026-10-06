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

    <h2 class="section-label">{{ kind === 'radio' ? 'Station' : kind === 'podcast' ? 'Podcast' : 'Audio' }}</h2>
    <template v-if="online">
      <div v-if="picked" class="card picked">
        <img v-if="picked.image" :src="picked.image" alt="" class="picked-img" />
        <span v-else class="picked-img picked-blank"><Icon :name="kind" :size="26" /></span>
        <span class="grow">
          <span class="title">{{ picked.name || check.info?.title || picked.url }}</span>
          <span v-if="check.state === 'checking'" class="sub">Checking it works…</span>
          <span v-else-if="check.state === 'error'" class="sub bad">{{ check.message }}</span>
          <span v-else-if="kind === 'podcast' && check.info" class="sub">Works · {{ check.info.count }} episodes · newest: “{{ check.info.newest_title }}”</span>
          <span v-else-if="check.state === 'ok'" class="sub">Works · {{ picked.author || 'live stream' }}</span>
        </span>
        <button class="btn btn-ghost" :disabled="uploading" @click="unpick">Change</button>
      </div>
      <template v-else>
        <form class="find" role="search" @submit.prevent="search">
          <input v-model="query" class="input" type="search" :placeholder="kind === 'radio' ? 'Search for a station, e.g. Fun Kids' : 'Search for a podcast, e.g. Circle Round'" :aria-label="kind === 'radio' ? 'Search for a station' : 'Search for a podcast'" />
          <button class="btn btn-soft" type="submit" :disabled="searching || query.trim().length < 2">
            <Icon :name="searching ? 'refresh' : 'search'" :size="20" /> Search
          </button>
        </form>
        <p v-if="searchError" class="find-note bad">{{ searchError }}</p>
        <p v-else-if="searched && !results.length && !searching" class="find-note">Nothing found. Try fewer words, or paste a link below.</p>
        <div v-if="results.length" class="results">
          <button v-for="r in results" :key="r.url" class="result" @click="pick(r)">
            <img v-if="r.thumb || r.image" :src="r.thumb || r.image" alt="" loading="lazy" />
            <span v-else class="result-blank"><Icon :name="kind" :size="20" /></span>
            <span class="grow">
              <span class="title">{{ r.name }}</span>
              <span class="sub ellipsis">{{ r.author }}<template v-if="r.episodes"> · {{ r.episodes }} {{ r.episodes === 1 ? 'episode' : 'episodes' }}</template></span>
            </span>
          </button>
        </div>
        <button class="btn btn-ghost btn-block" :aria-expanded="String(showLink)" @click="showLink = !showLink">
          <Icon name="link" :size="18" /> {{ kind === 'radio' ? 'Have a stream link?' : 'Have the podcast’s feed link?' }}
        </button>
        <form v-if="showLink" class="find" @submit.prevent="useLink">
          <input v-model="linkUrl" class="input" type="url" inputmode="url" placeholder="https://…" :aria-label="kind === 'radio' ? 'Stream link' : 'Feed link'" />
          <button class="btn btn-soft" type="submit" :disabled="!linkUrl.trim()">Use it</button>
        </form>
      </template>

      <template v-if="kind === 'podcast'">
        <h2 class="section-label">When the sticker is tapped, play</h2>
        <div role="radiogroup" aria-label="Which episode plays">
          <button v-for="m in episodeModes" :key="m.id" class="choice" role="radio" :aria-checked="episodeMode === m.id ? 'true' : 'false'" :disabled="uploading" @click="episodeMode = m.id">
            <span class="grow"><span class="title">{{ m.label }}</span><span class="sub">{{ m.hint }}</span></span>
          </button>
        </div>
      </template>
    </template>
    <template v-else-if="kind === 'song'">
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
      <input v-model="name" class="input" type="text" @input="nameTouched = true" :placeholder="{ story: 'Story name', album: 'Album name', radio: 'Station name', podcast: 'Podcast name' }[kind] || 'Song name'" :disabled="uploading" />
    </label>

    <h2 class="section-label">Cover <span class="opt">(optional)</span></h2>
    <div class="cover-row">
      <img v-if="coverPreview" :src="coverPreview" alt="Chosen cover" class="cover-preview" />
      <img v-else-if="online && picked?.image" :src="picked.image" alt="Cover from the directory" class="cover-preview" />
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
      <span v-if="online">Saving…</span>
      <span v-else>Uploading… {{ Math.round(progress * 100) }}%</span>
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
import { computed, reactive, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api, upload } from '../api'
import { shrinkImage } from '../covers'
import { store, loadSongs, openWriter, cancelWriting, toast } from '../store'
import Icon from '../components/Icon.vue'

const router = useRouter()
const types = [
  { id: 'story', label: 'Story', hint: 'Chapters, and it remembers where you got to', icon: 'book' },
  { id: 'album', label: 'Album', hint: 'Several songs, played in order', icon: 'disc' },
  { id: 'song', label: 'Song', hint: 'One audio file', icon: 'music' },
  { id: 'radio', label: 'Radio station', hint: 'Plays a live station from the internet', icon: 'radio' },
  { id: 'podcast', label: 'Podcast', hint: 'Plays episodes from the internet, nothing to download', icon: 'podcast' },
]
const episodeModes = [
  { id: 'newest', label: 'The newest episode', hint: 'Best for shows that come out every week' },
  { id: 'next', label: 'Episodes in order', hint: 'Starts at the first episode and moves on after each one finishes. Good for stories in parts.' },
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

// Radio and podcasts: found by search (or a pasted link), then checked by the box
const online = computed(() => kind.value === 'radio' || kind.value === 'podcast')
const query = ref('')
const results = ref([])
const searching = ref(false)
const searched = ref(false)
const searchError = ref('')
const showLink = ref(false)
const linkUrl = ref('')
const picked = ref(null)            // { name, author, url, image }
const check = reactive({ state: 'idle', message: '', info: null })
const episodeMode = ref('newest')

const ready = computed(() => {
  if (!name.value.trim()) return false
  if (online.value) return !!picked.value && check.state === 'ok'
  return kind.value === 'song' ? songFile.value : chapters.value.length
})

function setKind(k) {
  if (kind.value === k) return
  kind.value = k
  songFile.value = null
  chapters.value = []
  results.value = []
  searched.value = false
  searchError.value = ''
  unpick()
}

async function search() {
  const term = query.value.trim()
  if (term.length < 2) return
  searching.value = true
  searchError.value = ''
  try {
    const data = await api.get(`/find/${kind.value === 'radio' ? 'radio' : 'podcasts'}?q=${encodeURIComponent(term)}`)
    results.value = data.results || []
  } catch (e) {
    results.value = []
    searchError.value = e.message
  } finally {
    searching.value = false
    searched.value = true
  }
}

async function pick(item) {
  picked.value = { ...item }
  if (item.name && (!nameTouched.value || !name.value)) name.value = item.name
  check.state = 'checking'
  check.message = ''
  check.info = null
  try {
    const info = await api.post('/streams/check', { kind: kind.value, url: item.url })
    if (picked.value?.url !== item.url) return          // changed while checking
    check.info = info
    check.state = 'ok'
    if (!picked.value.image && info.image) picked.value.image = info.image
    if (info.title && !name.value) name.value = info.title
  } catch (e) {
    if (picked.value?.url !== item.url) return
    check.state = 'error'
    check.message = e.message
  }
}

function useLink() {
  const url = linkUrl.value.trim()
  if (url) pick({ name: '', author: '', url, image: '' })
}

function unpick() {
  picked.value = null
  check.state = 'idle'
  check.message = ''
  check.info = null
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
  fd.append('type', { story: 'audiobook', album: 'album', song: 'track' }[kind.value] || kind.value)
  fd.append('name', name.value.trim())
  if (cover.value) {
    const small = await shrinkImage(cover.value)
    fd.append('image', small, small.name || 'cover.jpg')
  }
  if (online.value) {
    // The box re-checks the address, and fetches the directory's picture
    // when no cover was chosen here
    fd.append('url', check.info?.url || picked.value.url)
    if (picked.value.image) fd.append('image_remote', picked.value.image)
    if (kind.value === 'podcast') fd.append('episode_mode', episodeMode.value)
  } else if (kind.value === 'song') {
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
.find { display: flex; gap: 8px; margin-bottom: 6px; }
.find .input { flex: 1; min-width: 0; }
.find .btn { flex-shrink: 0; }
.find-note { margin: 4px 4px 10px; font-size: 14px; color: var(--muted); }
.bad { color: var(--danger); }
.results { display: flex; flex-direction: column; gap: 4px; margin: 4px 0 8px; }
.result { display: flex; align-items: center; gap: 12px; padding: 8px 10px; min-height: 60px; border-radius: 14px; text-align: left; background: var(--card); }
.result img, .result-blank { width: 44px; height: 44px; border-radius: 10px; object-fit: cover; flex-shrink: 0; background: var(--ground); }
.result-blank, .picked-blank { display: grid; place-items: center; color: var(--blue); }
.result .grow, .picked .grow { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.result .title, .picked .title { font-weight: 700; }
.result .sub, .picked .sub { font-size: 13px; color: var(--muted); }
.picked .sub.bad { color: var(--danger); }
.picked { display: flex; align-items: center; gap: 12px; padding: 12px; }
.picked-img { width: 56px; height: 56px; border-radius: 12px; object-fit: cover; flex-shrink: 0; background: var(--ground); }
</style>
