import { wire } from "../api.js";

export default {
  data() {
    return { trails: [], gripe: "", rosterFor: null, roster: [] };
  },
  template: `
    <div>
      <h4 class="mb-3">Assigned treks</h4>
      <div v-if="gripe" class="alert alert-danger">{{ gripe }}</div>
      <table class="table align-middle">
        <thead><tr><th>Title</th><th>Turf</th><th>Slots</th><th>Registered</th><th>Phase</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="t in trails" :key="t.id">
            <td>{{ t.title }}</td><td>{{ t.turf }}</td>
            <td>
              <input type="number" min="0" :max="t.berths_total" class="form-control form-control-sm" style="width: 5rem;"
                     :value="t.berths_left" @change="setSlots(t, $event.target.value)" />
              / {{ t.berths_total }}
            </td>
            <td>{{ t.headcount }}</td>
            <td>
              <select class="form-select form-select-sm" :value="t.phase" @change="setPhase(t, $event.target.value)">
                <option v-for="p in ['Open','Closed']" :key="p">{{ p }}</option>
              </select>
            </td>
            <td>
              <button class="btn btn-sm btn-outline-secondary me-1" @click="viewRoster(t)">Roster</button>
              <button class="btn btn-sm btn-success" @click="wrapUp(t)">Mark complete</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="rosterFor" class="card mt-3">
        <div class="card-body">
          <h5>Roster — {{ rosterFor.title }}</h5>
          <ul class="list-group">
            <li class="list-group-item" v-for="r in roster" :key="r.id">
              {{ r.rover_name }} — {{ r.contact }} ({{ r.phase }})
            </li>
          </ul>
        </div>
      </div>
    </div>
  `,
  mounted() {
    this.refresh();
  },
  methods: {
    async refresh() {
      this.trails = await wire.get("/api/guide/trails");
    },
    async setSlots(trail, value) {
      try {
        await wire.put(`/api/guide/trails/${trail.id}`, { berths_left: Number(value) });
        await this.refresh();
      } catch (err) {
        this.gripe = err.message;
      }
    },
    async setPhase(trail, phase) {
      await wire.put(`/api/guide/trails/${trail.id}`, { phase });
      await this.refresh();
    },
    async wrapUp(trail) {
      await wire.put(`/api/guide/trails/${trail.id}/wrap-up`, {});
      await this.refresh();
    },
    async viewRoster(trail) {
      this.rosterFor = trail;
      this.roster = await wire.get(`/api/guide/trails/${trail.id}/rovers`);
    },
  },
};
