import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import Log from './views/Log.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/log', component: Log },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
