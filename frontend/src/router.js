import { createRouter, createWebHistory } from 'vue-router'
import LibraryView from './views/LibraryView.vue'
import ActivityView from './views/ActivityView.vue'
import SettingsView from './views/SettingsView.vue'
import StatusView from './views/StatusView.vue'
import AddView from './views/AddView.vue'

const routes = [
  { path: '/', component: LibraryView },
  { path: '/activity', component: ActivityView },
  { path: '/settings', component: SettingsView },
  { path: '/status', component: StatusView },
  { path: '/add', component: AddView },
  { path: '/log', redirect: '/activity' },          // old bookmark
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
