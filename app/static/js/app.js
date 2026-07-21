import { wire } from "./api.js";
import gate from "./views/gate.js";
import overseer from "./views/overseer.js";
import guide from "./views/guide.js";
import rover from "./views/rover.js";

const { createApp } = Vue;

createApp({
  components: { gate, overseer, guide, rover },
  data() {
    return { prowler: null, booting: true };
  },
  template: `
    <div>
      <nav class="navbar navbar-dark bg-dark mb-4" v-if="prowler">
        <div class="container-fluid">
          <span class="navbar-brand">TMA — {{ prowler.capacity }}</span>
          <div class="d-flex align-items-center text-white">
            <span class="me-3">{{ prowler.full_name }}</span>
            <button class="btn btn-outline-light btn-sm" @click="signOut">Sign out</button>
          </div>
        </div>
      </nav>
      <div class="container">
        <div v-if="booting" class="text-center text-muted mt-5">Loading…</div>
        <gate v-else-if="!prowler" :on-enter="settle" />
        <overseer v-else-if="prowler.capacity === 'overseer'" />
        <guide v-else-if="prowler.capacity === 'guide'" />
        <rover v-else :prowler="prowler" @profile-saved="settle" />
      </div>
    </div>
  `,
  async mounted() {
    try {
      const { prowler } = await wire.get("/api/auth/whoami");
      this.prowler = prowler;
    } finally {
      this.booting = false;
    }
  },
  methods: {
    settle(prowler) {
      this.prowler = prowler;
    },
    async signOut() {
      await wire.post("/api/auth/logout", {});
      this.prowler = null;
    },
  },
}).mount("#app");
