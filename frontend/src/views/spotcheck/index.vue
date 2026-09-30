<template>
  <section class="page" data-module="spotcheck">
    <header class="page-head">
      <div>
        <h2>点检记录管理</h2>
        <p class="page-desc">维护点检记录，围绕点检单号、关联计划、点检设备、点检人员做登记、筛选与状态流转。状态只能从待点检单向推进，提交时必须填写异常项数。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记点检记录</button>
        <button class="btn" type="button" @click="exportRows">导出点检记录清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <label class="filter-item">
        <span>点检状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ displayValue(row, column) }}</td>
          <td class="row-actions">
            <button
              v-for="action in availableActions(row)"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
            <span v-if="!availableActions(row).length" class="empty-inline">已办结</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无点检记录数据，可先登记点检记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条点检记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>

const ENDPOINT = '/api/spotcheck'
const columns = ["点检单号", "关联计划", "点检设备", "点检人员", "点检日期", "点检结论", "异常项数", "复核结论", "点检状态"]
// 状态 → 当前可执行的动作；已复核/已退回为终态，没有可执行动作，保证只能单向推进
const ACTIONS_BY_STATUS: Record<string, string[]> = {
  '待点检': ['开始点检'],
  '点检中': ['提交结果'],
  '已提交': ['复核通过', '退回重检'],
  '已复核': [],
  '已退回': [],
}
const statuses = ["待点检", "点检中", "已提交", "已复核", "已退回"]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const statusFilter = ref('')
const filterFields = columns.slice(0, 3)

const stats = computed(() => {
  const pending = rows.value.filter((row) => row.status === '待点检').length
  const committed = rows.value.filter((row) => ['已提交', '已复核', '已退回'].includes(String(row.status))).length
  const abnormal = rows.value.reduce(
    (sum, row) => sum + (Number(row.异常项数) > 0 ? 1 : 0),
    0,
  )
  return [
    { label: '待点检设备', value: pending },
    { label: '已提交点检单数', value: committed },
    { label: '异常项数', value: abnormal },
  ]
})

function availableActions(row: Row): string[] {
  return ACTIONS_BY_STATUS[String(row.status)] ?? []
}

function displayValue(row: Row, column: string): string {
  const value = row[column]
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function resetFilters() {
  filters.value = {}
  statusFilter.value = ''
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '点检记录登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  const values: Record<string, string | number> = { action }
  if (action === '提交结果') {
    const input = window.prompt('请输入本次点检发现的异常项数（无异常请填 0）', String(row.异常项数 ?? ''))
    if (input === null) return
    values['异常项数'] = input.trim()
    const conclusion = window.prompt('请输入点检结论（可留空）', String(row.点检结论 ?? ''))
    if (conclusion !== null && conclusion.trim() !== '') values['点检结论'] = conclusion.trim()
  } else if (action === '复核通过' || action === '退回重检') {
    const fallback = action === '复核通过' ? '复核通过' : '复核不通过，退回重检'
    const input = window.prompt('请输入复核结论', String(row.复核结论 ?? fallback))
    if (input === null) return
    values['复核结论'] = input.trim() || fallback
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values }),
    })
    if (!response.ok) {
      throw new Error('点检记录动作未生效，请稍后重试')
    }
    const payload = await response.json()
    if (payload && payload.ok === false) {
      errorMessage.value = payload.message || '点检记录操作被拒绝'
      return
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '点检记录操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) {
    if (value.trim()) params.set(key, value.trim())
  }
  if (statusFilter.value) params.set('status', statusFilter.value)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error('点检记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '点检记录列表读取失败'
  }
}

onMounted(reload)
</script>
