<template>
  <section class="page">
    <header class="page-head">
      <div>
        <h2>运营概览</h2>
        <p class="page-desc">汇总各业务模块的关键指标，先看总量再看异常。</p>
      </div>
    </header>
    <div class="stat-row">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>业务模块</th><th>今日新增</th><th>待处理</th><th>异常量</th></tr>
      </thead>
      <tbody>
        <tr v-for="row in moduleRows" :key="row.name">
          <td>{{ row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>

    <article v-if="spotcheckRow" class="review-panel">
      <h3>点检记录复核结论</h3>
      <div class="stat-row">
        <span class="stat-label">已复核单数</span>
        <strong class="stat-value">{{ spotcheckRow.reviewed }}</strong>
        <span class="stat-label">复核异常单数</span>
        <strong class="stat-value review-abnormal">{{ spotcheckRow.reviewAbnormal }}</strong>
      </div>
      <p class="page-desc">
        已提交并完成复核 {{ spotcheckRow.reviewed }} 单，其中复核结论含异常 {{ spotcheckRow.reviewAbnormal }} 单；
        待点检/点检中 {{ spotcheckRow.pending }} 单不计入复核异常。
      </p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'

type ModuleRow = {
  name: string
  created: number
  pending: number
  abnormal: number
  reviewed?: number
  reviewAbnormal?: number
}

type Overview = {
  cards: { label: string; value: number }[]
  modules: ModuleRow[]
}

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const spotcheckRow = computed(() => moduleRows.value.find(row => row.name === 'spotcheck'))

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = [{"name": "锅炉设备", "created": 0, "pending": 0, "abnormal": 0}, {"name": "压力容器", "created": 0, "pending": 0, "abnormal": 0}, {"name": "压力管道", "created": 0, "pending": 0, "abnormal": 0}, {"name": "起重机械", "created": 0, "pending": 0, "abnormal": 0}, {"name": "电梯设备", "created": 0, "pending": 0, "abnormal": 0}, {"name": "场内机动车辆", "created": 0, "pending": 0, "abnormal": 0}, {"name": "点检计划", "created": 0, "pending": 0, "abnormal": 0}, {"name": "点检记录", "created": 0, "pending": 0, "abnormal": 0}, {"name": "润滑保养", "created": 0, "pending": 0, "abnormal": 0}, {"name": "定期检验", "created": 0, "pending": 0, "abnormal": 0}, {"name": "检验报告", "created": 0, "pending": 0, "abnormal": 0}, {"name": "隐患登记", "created": 0, "pending": 0, "abnormal": 0}, {"name": "整改闭环", "created": 0, "pending": 0, "abnormal": 0}, {"name": "使用登记", "created": 0, "pending": 0, "abnormal": 0}, {"name": "作业人员", "created": 0, "pending": 0, "abnormal": 0}, {"name": "备件器材", "created": 0, "pending": 0, "abnormal": 0}, {"name": "维保合同", "created": 0, "pending": 0, "abnormal": 0}, {"name": "费用结算", "created": 0, "pending": 0, "abnormal": 0}]
  }
})
</script>

<style scoped>
.review-panel {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fafc;
}
.review-panel h3 { margin: 0 0 8px; font-size: 15px; }
.review-panel .stat-row { gap: 24px; }
.review-abnormal { color: #b42318; }
</style>
