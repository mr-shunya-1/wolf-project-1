import { wire } from "../api.js";

export default {
  props: ["prowler"],
  data() {
    return {
      tab: "browse",
      trails: [],
      history: [],
      gripe: "",
      filters: { grit: "", turf: "", max_span: "" },
      profileDraft: { full_name: "", contact: "", secret: "" },
      exportStatus: "",
    };
  },
  template: `
    <div>
      <ul class="nav nav-tabs mb-3">
        <li class="nav-item" v-for="t in ['browse','history','profile']" :key="t">
          <a class="nav-link" :class="{active: tab === t}" href="#" @click.prevent="tab = t">{{ t }}</a>
        </li>
      </ul>
      <div v-if="gripe" class="alert alert-danger">{{ gripe }}</div>

      <div v-if="tab === 'browse'">
        <div class="row g-2 mb-3">
          <div class="col-md-3">
            <select class="form-select" v-model="filters.grit" @change="loadTrails">
              <option value="">Any grit</option><option>Easy</option><option>Moderate</option><option>Hard</option>
            </select>
          </div>
          <div class="col-md-3"><input class="form-control" placeholder="Location" v-model.trim="filters.turf" @keyup.enter="loadTrails" /></div>
          <div class="col-md-3"><input type="number" class="form-control" placeholder="Max days" v-model.number="filters.max_span" @change="loadTrails" /></div>
          <div class="col-md-1"><button class="btn btn-outline-secondary w-100" @click="loadTrails">Filter</button></div>
        </div>
        <div class="row g-3">
          <div class="col-md-4" v-for="t in trails" :key="t.id">
            <div class="card h-100">
              <div class="card-body">
                <h5 class="card-title">{{ t.title }}</h5>
                <p class="mb-1 text-muted">{{ t.turf }} · {{ t.grit }} · {{ t.span_days }}d</p>
                <p class="mb-2">{{ t.berths_left }} / {{ t.berths_total }} slots left</p>
                <button class="btn btn-primary btn-sm" :disabled="t.berths_left <= 0" @click="book(t)">Book</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="tab === 'history'">
        <button class="btn btn-outline-secondary btn-sm mb-2" @click="exportHistory">Export as CSV</button>
        <span class="ms-2 text-muted">{{ exportStatus }}</span>
        <table class="table table-sm mt-2">
          <thead><tr><th>Trail</th><th>Turf</th><th>Phase</th><th>Logged</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in history" :key="p.id">
              <td>{{ p.trail_title }}</td><td>{{ p.turf }}</td><td>{{ p.phase }}</td>
              <td>{{ p.logged_at?.slice(0,10) }}</td>
              <td><button v-if="p.phase === 'Booked'" class="btn btn-sm btn-outline-danger" @click="cancel(p)">Cancel</button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tab === 'profile'">
        <div class="card" style="max-width: 24rem;">
          <div class="card-body">
            <div class="mb-2">
              <label class="form-label">Full name</label>
              <input class="form-control" v-model.trim="profileDraft.full_name" />
            </div>
            <div class="mb-2">
              <label class="form-label">Contact</label>
              <input class="form-control" v-model.trim="profileDraft.contact" />
            </div>
            <div class="mb-3">
              <label class="form-label">New secret (optional)</label>
              <input class="form-control" type="password" minlength="6" v-model="profileDraft.secret" />
            </div>
            <button class="btn btn-primary" @click="saveProfile">Save</button>
          </div>
        </div>
      </div>
    </div>
  `,
  mounted() {
    this.loadTrails();
    this.loadHistory();
    this.profileDraft.full_name = this.prowler.full_name;
    this.profileDraft.contact = this.prowler.contact || "";
  },
  methods: {
    async loadTrails() {
      const params = new URLSearchParams();
      if (this.filters.grit) params.set("grit", this.filters.grit);
      if (this.filters.turf) params.set("turf", this.filters.turf);
      if (this.filters.max_span) params.set("max_span", this.filters.max_span);
      this.trails = await wire.get(`/api/rover/trails?${params}`);
    },
    async loadHistory() {
      this.history = await wire.get("/api/rover/passages");
    },
    async book(trail) {
      this.gripe = "";
      try {
        await wire.post(`/api/rover/trails/${trail.id}/book`, {});
        await this.loadTrails();
        await this.loadHistory();
      } catch (err) {
        this.gripe = err.message;
      }
    },
    async cancel(passage) {
      await wire.put(`/api/rover/passages/${passage.id}/cancel`, {});
      await this.loadTrails();
      await this.loadHistory();
    },
    async saveProfile() {
      this.gripe = "";
      try {
        const updated = await wire.put("/api/auth/profile", this.profileDraft);
        this.profileDraft.secret = "";
        this.$emit("profile-saved", updated);
      } catch (err) {
        this.gripe = err.message;
      }
    },
    async exportHistory() {
      this.exportStatus = "queued…";
      const { job_id } = await wire.post("/api/rover/export", {});
      const poll = async () => {
        const outcome = await wire.get(`/api/rover/export/${job_id}`);
        if (outcome.status === "pending") {
          this.exportStatus = "still working…";
          setTimeout(poll, 1500);
        } else {
          this.exportStatus = "done!";
          window.open(outcome.download, "_blank");
        }
      };
      poll();
    },
  },
};
