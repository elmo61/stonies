<template>
  <nav class="navbar is-dark" role="navigation" aria-label="main navigation">
    <div class="navbar-brand">
      <router-link class="navbar-item has-text-weight-bold" to="/">Stonies</router-link>
    </div>
    <div class="navbar-menu is-active" style="background: transparent; box-shadow: none; padding: 0;">
      <div class="navbar-end">
        <router-link class="navbar-item" to="/" exact-active-class="is-active">Home</router-link>
        <router-link class="navbar-item" to="/log" exact-active-class="is-active">Activity Log</router-link>
      </div>
    </div>
  </nav>
  <router-view />
</template>
