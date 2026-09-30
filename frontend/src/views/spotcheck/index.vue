<template>
  <section class="page" data-module="spotcheck">
    <header class="page-head">
      <div>
        <h2>点检记录管理</h2>
        <p class="page-desc">维护点检记录，围绕点检单号、关联计划、点检设备、点检人员做登记、筛选与状态流转。</p>
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
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
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
            <span v-if="!availableActions(row).length" class="muted">—</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无点检记录数据，可先登记点检记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条点检记录记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | boolean | null>

const ENDPOINT = '/api/spotcheck'
const columns = ["点检单号", "关联计划", "点检设备", "点检人员", "点检日期", "点检结论", "异常项数", "点检状态"]
// 各状态下只露出允许的下一步动作，配合后端状态机实现单向推进
const ACTIONS_BY_STATUS: Record<string, string[]> = {
  "待点检": ["开始点检"],
  "点检中": ["提交结果"],
  "已提交": ["退回重检"],
  "已退回": [],
}
const statusField = "点检状态"

const rows = ref<Row[]>([])
const allRows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

// 待点检设备：仍在待处理口径（待点检/点检中）内的单数；异常项数汇总已提交的复核结论
const stats = computed(() => {
  const pending = allRows.value.filter(row => String(row.status) === "待点检" || String(row.status) === "点检中").length
  const abnormalTotal = allRows.value.reduce((sum, row) => {
    const count = Number(row["异常项数"])
    return String(row.status) === "已提交" && Number.isInteger(count) && count > 0 ? sum + count : sum
  }, 0)
  const currentMonth = new Date().toISOString().slice(0, 7)
  const monthCount = allRows.value.filter(row => String(row["点检日期"] ?? "").slice(0, 7) === currentMonth).length
  return [
    { label: "待点检设备", value: pending },
    { label: "本月点检单数", value: monthCount },
    { label: "异常项数", value: abnormalTotal },
  ]
})

function availableActions(row: Row): string[] {
  return ACTIONS_BY_STATUS[String(row.status ?? row[statusField] ?? "")] ?? []
}

function resetFilters() {
  filters.value = {}
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
  const payload: Record<string, unknown> = { action }
  if (action === "提交结果") {
    const countInput = window.prompt('请输入异常项数（0 或正整数），空记录不能提交')
    if (countInput === null) {
      return
    }
    const count = countInput.trim()
    if (!/^\d+$/.test(count)) {
      errorMessage.value = '异常项数必须是 0 或正整数，提交已取消'
      return
    }
    const conclusion = window.prompt('请输入点检/复核结论（可留空）') ?? ''
    payload["异常项数"] = Number(count)
    if (conclusion.trim()) {
      payload["点检结论"] = conclusion.trim()
    }
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error('点检记录动作未生效，请稍后重试')
    }
    const result = (await response.json()) as { ok: boolean; message: string }
    // 后端业务校验失败时 HTTP 仍是 200，必须读取 ok 字段，否则失败原因会被吞掉
    if (!result.ok) {
      errorMessage.value = result.message || '点检记录动作未生效'
      return
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '点检记录操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const [listResponse, statsResponse] = await Promise.all([
      request(`${ENDPOINT}?${query}`),
      request(`${ENDPOINT}?page=1&size=200`),
    ])
    if (!listResponse.ok) {
      throw new Error('点检记录列表读取失败')
    }
    const payload = await listResponse.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (statsResponse.ok) {
      const statsPayload = await statsResponse.json()
      allRows.value = statsPayload.items ?? []
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '点检记录列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.muted { color: var(--muted); }
</style>
