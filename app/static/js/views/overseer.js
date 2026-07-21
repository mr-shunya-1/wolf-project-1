import { wire } from "../api.js";

export default {
  data() {
    return {
      tab: "overview",
      counts: { trail_count: 0, rover_count: 0, guide_count: 0, passage_count: 0 },
      favourites: [],
      trails: [],
      guides: [],
      wayfarers: [],
      passages: [],
      searchTerm: "",
      searchKind: "trails",
      searchHits: [],
      gripe: "",
      trailDraft: { title: "", turf: "", grit: "Moderate", span_days: 3, berths_total: 10, outset: "", homecoming: "" },
      guideDraft: { handle: "", secret: "", full_name: "", contact: "" },
      assignPickFor: null,
      chartHandle: null,
    };
  },
  template: `
    <div>
      <ul class="nav nav-tabs mb-3">
        <li class="nav-item" v-for="t in ['overview','trails','guides','people','bookings','search']" :key="t">
          <a class="nav-link" :class="{active: tab === t}" href="#" @click.prevent="switchTo(t)">{{ t }}</a>
        </li>
      </ul>
      <div v-if="gripe" class="alert alert-danger">{{ gripe }}</div>

      <div v-if="tab === 'overview'">
        <div class="row g-3 mb-4">
          <div class="col-md-3" v-for="card in overviewCards" :key="card.label">
            <div class="card text-center shadow-sm">
              <div class="card-body">
                <div class="display-6">{{ card.value }}</div>
                <div class="text-muted">{{ card.label }}</div>
              </div>
            </div>
          </div>
        </div>
        <canvas id="favourites-chart" height="90"></canvas>
      </div>

      <div v-if="tab === 'trails'">
        <div class="card mb-3">
          <div class="card-body">
            <h5>Carve a new trail</h5>
            <div class="row g-2">
              <div class="col-md-3"><input class="form-control" placeholder="Title" v-model.trim="trailDraft.title" /></div>
              <div class="col-md-2"><input class="form-control" placeholder="Location" v-model.trim="trailDraft.turf" /></div>
              <div class="col-md-2">
                <select class="form-select" v-model="trailDraft.grit">
                  <option>Easy</option><option>Moderate</option><option>Hard</option>
                </select>
              </div>
              <div class="col-md-1"><input type="number" min="1" class="form-control" placeholder="Days" v-model.number="trailDraft.span_days" /></div>
              <div class="col-md-1"><input type="number" min="1" class="form-control" placeholder="Slots" v-model.number="trailDraft.berths_total" /></div>
              <div class="col-md-1"><input type="date" class="form-control" v-model="trailDraft.outset" /></div>
              <div class="col-md-1"><input type="date" class="form-control" v-model="trailDraft.homecoming" /></div>
              <div class="col-md-1"><button class="btn btn-primary w-100" @click="carveTrail">Add</button></div>
            </div>
          </div>
        </div>
        <table class="table table-sm align-middle">
          <thead><tr><th>Title</th><th>Turf</th><th>Grit</th><th>Slots</th><th>Warden</th><th>Phase</th><th></th></tr></thead>
          <tbody>
            <tr v-for="t in trails" :key="t.id">
              <td>{{ t.title }}</td><td>{{ t.turf }}</td><td>{{ t.grit }}</td>
              <td>{{ t.berths_left }}/{{ t.berths_total }}</td>
              <td>{{ t.warden_name || '—' }}</td>
              <td>
                <select class="form-select form-select-sm" :value="t.phase" @change="setPhase(t, $event.target.value)">
                  <option v-for="p in ['Pending','Approved','Open','Closed','Completed']" :key="p">{{ p }}</option>
                </select>
              </td>
              <td>
                <select class="form-select form-select-sm" @change="assignGuide(t, $event.target.value)">
                  <option value="">assign guide…</option>
                  <option v-for="g in guides" :key="g.id" :value="g.id">{{ g.full_name }}</option>
                </select>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tab === 'guides'">
        <div class="card mb-3">
          <div class="card-body">
            <h5>Recruit trek staff</h5>
            <div class="row g-2">
              <div class="col-md-3"><input class="form-control" placeholder="Handle" v-model.trim="guideDraft.handle" /></div>
              <div class="col-md-3"><input class="form-control" placeholder="Full name" v-model.trim="guideDraft.full_name" /></div>
              <div class="col-md-3"><input class="form-control" placeholder="Contact" v-model.trim="guideDraft.contact" /></div>
              <div class="col-md-2"><input class="form-control" type="password" placeholder="Secret" v-model="guideDraft.secret" /></div>
              <div class="col-md-1"><button class="btn btn-primary w-100" @click="recruitGuide">Add</button></div>
            </div>
          </div>
        </div>
        <table class="table table-sm">
          <thead><tr><th>Handle</th><th>Name</th><th>Contact</th><th>Standing</th><th></th></tr></thead>
          <tbody>
            <tr v-for="g in guides" :key="g.id">
              <td>{{ g.handle }}</td><td>{{ g.full_name }}</td><td>{{ g.contact }}</td><td>{{ g.standing }}</td>
              <td><button class="btn btn-sm btn-outline-secondary" @click="toggleStanding(g)">
                {{ g.standing === 'active' ? 'Bench' : 'Reinstate' }}
              </button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tab === 'people'">
        <table class="table table-sm">
          <thead><tr><th>Handle</th><th>Name</th><th>Role</th><th>Standing</th><th></th></tr></thead>
          <tbody>
            <tr v-for="w in wayfarers" :key="w.id">
              <td>{{ w.handle }}</td><td>{{ w.full_name }}</td><td>{{ w.capacity }}</td><td>{{ w.standing }}</td>
              <td><button class="btn btn-sm btn-outline-secondary" @click="toggleStanding(w)">
                {{ w.standing === 'active' ? 'Bench' : 'Reinstate' }}
              </button></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tab === 'bookings'">
        <table class="table table-sm">
          <thead><tr><th>Trail</th><th>Turf</th><th>Phase</th><th>Toll</th><th>Logged</th></tr></thead>
          <tbody>
            <tr v-for="p in passages" :key="p.id">
              <td>{{ p.trail_title }}</td><td>{{ p.turf }}</td><td>{{ p.phase }}</td><td>{{ p.toll_state }}</td>
              <td>{{ p.logged_at?.slice(0,10) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tab === 'search'">
        <div class="input-group mb-3" style="max-width: 30rem;">
          <select class="form-select" style="max-width: 8rem;" v-model="searchKind">
            <option value="trails">Trails</option>
            <option value="people">People</option>
          </select>
          <input class="form-control" v-model="searchTerm" @keyup.enter="runSearch" placeholder="search…" />
          <button class="btn btn-outline-secondary" @click="runSearch">Go</button>
        </div>
        <pre>{{ searchHits }}</pre>
      </div>
    </div>
  `,
  computed: {
    overviewCards() {
      return [
        { label: "Treks", value: this.counts.trail_count },
        { label: "Trekkers", value: this.counts.rover_count },
        { label: "Staff", value: this.counts.guide_count },
        { label: "Bookings", value: this.counts.passage_count },
      ];
    },
  },
  mounted() {
    this.refreshAll();
  },
  methods: {
    async refreshAll() {
      try {
        this.counts = await wire.get("/api/overseer/dashboard");
        const st = await wire.get("/api/overseer/stats");
        this.favourites = st.favourites;
        this.trails = await wire.get("/api/overseer/trails");
        this.guides = await wire.get("/api/overseer/guides");
        this.wayfarers = await wire.get("/api/overseer/wayfarers");
        this.passages = await wire.get("/api/overseer/passages");
        this.$nextTick(() => this.paintChart());
      } catch (err) {
        this.gripe = err.message;
      }
    },
    switchTo(t) {
      this.tab = t;
      if (t === "overview") this.$nextTick(() => this.paintChart());
    },
    paintChart() {
      const canvas = document.getElementById("favourites-chart");
      if (!canvas || !window.Chart) return;
      if (this.chartHandle) this.chartHandle.destroy();
      this.chartHandle = new Chart(canvas, {
        type: "bar",
        data: {
          labels: this.favourites.map((f) => f.title),
          datasets: [{ label: "Participants", data: this.favourites.map((f) => f.headcount) }],
        },
      });
    },
    async carveTrail() {
      this.gripe = "";
      try {
        await wire.post("/api/overseer/trails", this.trailDraft);
        this.trailDraft = { title: "", turf: "", grit: "Moderate", span_days: 3, berths_total: 10, outset: "", homecoming: "" };
        this.trails = await wire.get("/api/overseer/trails");
        this.counts = await wire.get("/api/overseer/dashboard");
      } catch (err) {
        this.gripe = err.message;
      }
    },
    async setPhase(trail, phase) {
      await wire.put(`/api/overseer/trails/${trail.id}`, { phase });
      this.trails = await wire.get("/api/overseer/trails");
    },
    async assignGuide(trail, guideId) {
      if (!guideId) return;
      await wire.post(`/api/overseer/trails/${trail.id}/assign`, { guide_id: Number(guideId) });
      this.trails = await wire.get("/api/overseer/trails");
    },
    async recruitGuide() {
      this.gripe = "";
      try {
        await wire.post("/api/overseer/guides", this.guideDraft);
        this.guideDraft = { handle: "", secret: "", full_name: "", contact: "" };
        this.guides = await wire.get("/api/overseer/guides");
      } catch (err) {
        this.gripe = err.message;
      }
    },
    async toggleStanding(person) {
      const wanted = person.standing === "active" ? "benched" : "active";
      await wire.put(`/api/overseer/wayfarers/${person.id}/standing`, { standing: wanted });
      this.guides = await wire.get("/api/overseer/guides");
      this.wayfarers = await wire.get("/api/overseer/wayfarers");
    },
    async runSearch() {
      this.searchHits = await wire.get(`/api/overseer/search?q=${encodeURIComponent(this.searchTerm)}&kind=${this.searchKind}`);
    },
  },
};
