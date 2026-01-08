<template>
  <div class="aideo-app">
    <h1>📁 AIDEO : Gestionnaire de Documents</h1>
    
    <div class="upload-box">
        <input type="file" @change="onFileSelected" accept="image/*,application/pdf" />      <button @click="scan" :disabled="loading || !file">
        {{ loading ? 'IA en cours...' : 'Analyser le document' }}
      </button>
    </div>

    <div class="grid">
      <div v-for="doc in docs" :key="doc.id" class="card">
        <h3>{{ doc.ai_type || 'Analyse...' }} <small>#{{ doc.id }}</small></h3>
        <p>{{ doc.ai_resume || 'L\'IA n\'a pas encore résumé ce fichier.' }}</p>
        <div class="tags">
          <span v-for="a in doc.ai_actions" :key="a" class="tag">⚡ {{ a }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const docs = ref([])
const file = ref(null)
const loading = ref(false)
const API = "http://localhost:8000/api/v1"

const load = async () => {
  const r = await axios.get(`${API}/documents/`)
  docs.value = r.data.sort((a,b) => b.id - a.id)
}

const scan = async () => {
  loading.value = true
  const fd = new FormData(); fd.append('file', file.value)
  try {
    await axios.post(`${API}/documents/scan`, fd)
    await load()
  } finally { loading.value = false }
}

onMounted(load)
</script>

<style>
.aideo-app { font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; }
.upload-box { border: 2px dashed #ccc; padding: 20px; text-align: center; margin-bottom: 20px; border-radius: 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
.card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #fafafa; }
.tag { background: #e3f2fd; font-size: 0.8em; padding: 3px 8px; border-radius: 4px; margin-right: 5px; }
button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
button:disabled { background: #ccc; }
</style>