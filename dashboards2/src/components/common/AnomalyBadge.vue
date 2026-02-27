<template>
  <span v-if="flag === 'HIGH'" class="badge bg-danger text-white">🚨 CHER</span>
  <span v-else-if="flag === 'GOOD_DEAL'" class="badge bg-success text-white">🎉 AFFAIRE</span>
  <span v-else class="text-gray-400 text-xs">—</span>
</template>

<script setup>
defineProps({
  flag: {
    type: String,
    default: null
  }
})
</script>

<style scoped>
.bg-success {
  background-color: #10B981;
}
</style>
