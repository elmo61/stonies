<template>
  <nav class="stonies-nav" role="navigation">
    <router-link to="/" class="stonies-brand">
      <!-- Stone with NFC tap waves — the core mechanic of the app -->
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <ellipse cx="14" cy="20" rx="11" ry="7" fill="#5b8dee"/>
        <ellipse cx="11" cy="17.5" rx="4" ry="2.2" fill="rgba(255,255,255,0.18)" transform="rotate(-20 11 17.5)"/>
        <path d="M11 12.5 Q14 8.5 17 12.5" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M8.5 9.5 Q14 3.5 19.5 9.5" stroke="rgba(255,255,255,0.45)" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span>Stonies</span>
    </router-link>

    <div class="stonies-links">
      <router-link to="/" exact-active-class="is-active">Home</router-link>
      <router-link to="/log" exact-active-class="is-active">Logs</router-link>
    </div>
  </nav>
  <router-view />
</template>

<style scoped>
.stonies-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  height: 46px;
  background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
  position: sticky;
  top: 0;
  z-index: 100;
}

@media (min-width: 769px) {
  .stonies-nav {
    height: 54px;
    padding: 0 1.75rem;
  }
}

.stonies-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
  text-decoration: none;
  font-weight: 700;
  font-size: 1.05rem;
  letter-spacing: 0.04em;
}

.stonies-brand svg {
  flex-shrink: 0;
}

.stonies-links {
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.stonies-links a {
  color: rgba(255, 255, 255, 0.65);
  text-decoration: none;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  font-size: 0.88rem;
  font-weight: 500;
  transition: color 0.15s, background 0.15s;
}

.stonies-links a:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.stonies-links a.is-active {
  color: white;
  background: rgba(255, 255, 255, 0.15);
}
</style>
