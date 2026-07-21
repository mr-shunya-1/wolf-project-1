import { wire } from "../api.js";

export default {
  props: ["onEnter"],
  data() {
    return {
      wantsRegister: false,
      handle: "",
      secret: "",
      full_name: "",
      contact: "",
      gripe: "",
      busy: false,
    };
  },
  template: `
    <div class="d-flex justify-content-center align-items-center" style="min-height: 80vh;">
      <div class="card shadow-sm" style="width: 24rem;">
        <div class="card-body">
          <h4 class="card-title mb-3">{{ wantsRegister ? 'Join as a Trekker' : 'Sign in' }}</h4>
          <div v-if="gripe" class="alert alert-danger py-2">{{ gripe }}</div>
          <form @submit.prevent="submit" novalidate>
            <div class="mb-2">
              <label class="form-label">Handle</label>
              <input v-model.trim="handle" required minlength="2" class="form-control" />
            </div>
            <div v-if="wantsRegister" class="mb-2">
              <label class="form-label">Full name</label>
              <input v-model.trim="full_name" required class="form-control" />
            </div>
            <div v-if="wantsRegister" class="mb-2">
              <label class="form-label">Contact (email)</label>
              <input v-model.trim="contact" type="email" class="form-control" />
            </div>
            <div class="mb-3">
              <label class="form-label">Secret</label>
              <input v-model="secret" type="password" required minlength="6" class="form-control" />
            </div>
            <button class="btn btn-primary w-100" :disabled="busy" type="submit">
              {{ wantsRegister ? 'Create account' : 'Sign in' }}
            </button>
          </form>
          <button class="btn btn-link mt-2 w-100" @click="wantsRegister = !wantsRegister">
            {{ wantsRegister ? 'Already have an account? Sign in' : 'New trekker? Register here' }}
          </button>
          <p class="text-muted small mt-2 mb-0">Only trekkers can self-register. Admin and staff accounts are provisioned for you.</p>
        </div>
      </div>
    </div>
  `,
  methods: {
    async submit() {
      this.gripe = "";
      this.busy = true;
      try {
        if (this.wantsRegister) {
          await wire.post("/api/auth/register", {
            handle: this.handle,
            secret: this.secret,
            full_name: this.full_name,
            contact: this.contact,
          });
        }
        const prowler = await wire.post("/api/auth/login", { handle: this.handle, secret: this.secret });
        this.onEnter(prowler);
      } catch (err) {
        this.gripe = err.message;
      } finally {
        this.busy = false;
      }
    },
  },
};
