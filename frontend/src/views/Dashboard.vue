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
          <td>{{ moduleLabels[row.name] ?? row.name }}</td>
          <td>{{ row.created }}</td>
          <td>{{ row.pending }}</td>
          <td>{{ row.abnormal }}</td>
        </tr>
      </tbody>
    </table>

    <header class="page-head">
      <div>
        <h2>点检记录复核</h2>
        <p class="page-desc">复核结论同步到看板：待复核记录需要尽快处理，退回重检的记录要核对异常项后重新提交。</p>
      </div>
    </header>
    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">待复核</span>
        <strong class="stat-value">{{ review.pending_review }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">复核通过</span>
        <strong class="stat-value">{{ review.approved }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">退回重检</span>
        <strong class="stat-value">{{ review.rejected }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">提交异常量</span>
        <strong class="stat-value">{{ review.abnormal_committed }}</strong>
      </article>
    </div>
    <table class="data-table">
      <thead>
        <tr><th>点检单号</th><th>点检状态</th><th>复核结论</th></tr>
      </thead>
      <tbody>
        <tr v-for="item in review.latest" :key="item.点检单号">
          <td>{{ item.点检单号 }}</td>
          <td>{{ item.点检状态 }}</td>
          <td>{{ item.复核结论 }}</td>
        </tr>
        <tr v-if="!review.latest.length">
          <td colspan="3" class="empty-state">暂无已出具复核结论的点检记录</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { fetchJson } from '@/api/client'

type Overview = {
  cards: { label: string; value: number }[]
  modules: { name: string; created: number; pending: number; abnormal: number }[]
  spotcheck_review: ReviewSummary
}

type ReviewSummary = {
  pending_review: number
  approved: number
  rejected: number
  abnormal_committed: number
  latest: { 点检单号: string; 点检状态: string; 复核结论: string }[]
}

const moduleLabels: Record<string, string> = {
  boiler: '锅炉设备',
  vessel: '压力容器',
  pressurepipe: '压力管道',
  crane: '起重机械',
  elevator: '电梯设备',
  forklift: '场内机动车辆',
  plan: '点检计划',
  spotcheck: '点检记录',
  lubricate: '润滑保养',
  inspect: '定期检验',
  report: '检验报告',
  hazard: '隐患登记',
  rectify: '整改闭环',
  register: '使用登记',
  operator: '作业人员',
  spare: '备件器材',
  contract: '维保合同',
  settle: '费用结算',
}

const emptyReview = (): ReviewSummary => ({
  pending_review: 0,
  approved: 0,
  rejected: 0,
  abnormal_committed: 0,
  latest: [],
})

const cards = ref<Overview['cards']>([])
const moduleRows = ref<Overview['modules']>([])
const review = reactive<ReviewSummary>(emptyReview())

onMounted(async () => {
  try {
    const payload = await fetchJson<Overview>('/api/overview')
    cards.value = payload.cards
    moduleRows.value = payload.modules
    Object.assign(review, payload.spotcheck_review ?? emptyReview())
  } catch {
    cards.value = [{"label": "业务模块", "value": 0}, {"label": "今日新增", "value": 0}]
    moduleRows.value = []
    Object.assign(review, emptyReview())
  }
})
</script>
