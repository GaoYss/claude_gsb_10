<template>
  <div class="page" v-loading="loading">
    <PageHeader :title="space.name || '绿地档案'" :description="`绿地编号 ${space.code || '-'}`">
      <template #tag>
        <EnumTag v-if="space.status" group="green_space_status" :value="space.status" :label="space.status_label" />
      </template>
      <template #actions>
        <el-button :icon="'Back'" @click="router.push('/green-spaces')">返回台账</el-button>
        <el-button type="primary" :icon="'Edit'" @click="formDialog.open(space)">编辑台账</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="所属行政区">{{ space.district || '-' }}</el-descriptions-item>
        <el-descriptions-item label="绿地类型">
          <EnumTag group="green_space_type" :value="space.green_type" :label="space.green_type_label" />
        </el-descriptions-item>
        <el-descriptions-item label="养护等级">
          <EnumTag group="maintenance_grade" :value="space.maintenance_grade" :label="space.maintenance_grade_label" />
        </el-descriptions-item>
        <el-descriptions-item label="绿地面积">{{ formatArea(space.area_sqm) }}</el-descriptions-item>
        <el-descriptions-item label="养护负责人">{{ space.manager || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ space.contact_phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="建成日期">{{ formatDate(space.established_date) }}</el-descriptions-item>
        <el-descriptions-item label="详细地址" :span="2">{{ space.address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="主要植物" :span="3">{{ space.plant_summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">{{ space.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="stat-grid">
      <StatCard label="养护记录" :value="formatNumber(statistics.record_count)" unit="条"
                :hint="`累计工时 ${formatHours(statistics.total_work_hours)}`" icon="Notebook" />
      <StatCard label="最近养护日期" :value="formatDate(statistics.last_maintenance_date)"
                :hint="statistics.is_maintenance_overdue ? '已超过 30 天未养护' : '养护节奏正常'"
                :tone="statistics.is_maintenance_overdue ? 'warning' : 'default'" icon="Calendar" />
      <StatCard label="绿植更换" :value="formatNumber(statistics.replacement_quantity)"
                :hint="`共 ${formatNumber(statistics.replacement_count)} 次，金额 ${formatCurrency(statistics.replacement_amount)}`"
                icon="Cherry" />
      <StatCard label="养护任务" :value="formatNumber(taskTotal)" unit="项"
                :hint="`已完成 ${statistics.task_status.completed || 0} 项，进行中 ${(statistics.task_status.in_progress || 0) + (statistics.task_status.pending || 0)} 项`"
                tone="info" icon="Tickets" />
      <StatCard label="废弃物待处置" :value="formatNumber(statistics.waste_pending_quantity ?? 0)"
                :hint="`产生 ${formatNumber(statistics.waste_produced_quantity ?? 0)}，已处置 ${formatNumber(statistics.waste_disposed_quantity ?? 0)}（${formatNumber(statistics.waste_count ?? 0)} 条）`"
                :tone="(statistics.waste_pending_quantity ?? 0) > 0 ? 'warning' : 'default'" icon="Van" />
    </div>

    <div class="panel">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="近期养护任务" name="tasks">
          <div class="tab-actions">
            <el-button link type="primary" @click="goList('tasks')">查看全部养护任务</el-button>
          </div>
          <el-table :data="recentTasks" size="small" empty-text="暂无养护任务">
            <el-table-column prop="task_no" label="任务编号" width="160" />
            <el-table-column prop="title" label="任务名称" min-width="160" show-overflow-tooltip />
            <el-table-column label="养护类型" width="120">
              <template #default="{ row }">
                <EnumTag group="task_type" :value="row.task_type" :label="row.task_type_label" />
              </template>
            </el-table-column>
            <el-table-column prop="plan_date" label="计划日期" width="110" />
            <el-table-column label="优先级" width="90">
              <template #default="{ row }">
                <EnumTag group="task_priority" :value="row.priority" :label="row.priority_label" />
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <EnumTag group="task_status" :value="row.status" :label="row.status_label" />
              </template>
            </el-table-column>
            <el-table-column prop="executor" label="执行班组" width="120">
              <template #default="{ row }">{{ row.executor || '-' }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="近期养护记录" name="records">
          <div class="tab-actions">
            <el-button link type="primary" @click="goList('records')">查看全部养护记录</el-button>
          </div>
          <el-table :data="recentRecords" size="small" empty-text="暂无养护记录">
            <el-table-column prop="record_no" label="记录编号" width="160" />
            <el-table-column prop="record_date" label="养护日期" width="110" />
            <el-table-column prop="work_content" label="作业内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="worker" label="作业人员" width="110">
              <template #default="{ row }">{{ row.worker || '-' }}</template>
            </el-table-column>
            <el-table-column label="工时" width="90">
              <template #default="{ row }">{{ formatHours(row.work_hours) }}</template>
            </el-table-column>
            <el-table-column label="质量评定" width="100">
              <template #default="{ row }">
                <EnumTag group="quality_result" :value="row.quality_result" :label="row.quality_result_label" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="近期绿植更换" name="replacements">
          <div class="tab-actions">
            <el-button link type="primary" @click="goList('replacements')">查看全部更换记录</el-button>
          </div>
          <el-table :data="recentReplacements" size="small" empty-text="暂无更换记录">
            <el-table-column prop="replacement_no" label="编号" width="160" />
            <el-table-column prop="replace_date" label="更换日期" width="110" />
            <el-table-column prop="plant_name" label="植株名称" width="130" />
            <el-table-column prop="spec" label="规格" width="130">
              <template #default="{ row }">{{ row.spec || '-' }}</template>
            </el-table-column>
            <el-table-column label="数量" width="110">
              <template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit_label }}</template>
            </el-table-column>
            <el-table-column label="更换原因" width="120">
              <template #default="{ row }">
                <EnumTag group="replacement_reason" :value="row.reason" :label="row.reason_label" />
              </template>
            </el-table-column>
            <el-table-column label="金额" width="120" align="right">
              <template #default="{ row }">{{ formatCurrency(row.amount) }}</template>
            </el-table-column>
          </el-table>

          <div v-if="replacementSummary.length" class="replacement-summary">
            <span class="summary-text">更换原因汇总：</span>
            <el-tag v-for="item in replacementSummary" :key="item.reason" class="summary-tag" type="info" effect="plain">
              {{ item.reason_label }} {{ formatNumber(item.quantity) }} 单位 / {{ formatCurrency(item.amount) }}
            </el-tag>
          </div>
        </el-tab-pane>

        <el-tab-pane label="近期废弃物处置" name="wastes">
          <div class="tab-actions">
            <el-button link type="primary" @click="goList('wastes')">查看全部废弃物</el-button>
          </div>
          <el-table :data="recentWastes" size="small" empty-text="暂无废弃物处置记录">
            <el-table-column prop="waste_no" label="编号" width="160" />
            <el-table-column prop="produce_date" label="产生日期" width="100" />
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <EnumTag group="green_waste_type" :value="row.waste_type" :label="row.waste_type_label" />
              </template>
            </el-table-column>
            <el-table-column label="产生量" width="100">
              <template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit_label }}</template>
            </el-table-column>
            <el-table-column label="处置方式" width="110">
              <template #default="{ row }">
                <EnumTag v-if="row.disposal_method" group="disposal_method"
                         :value="row.disposal_method" :label="row.disposal_method_label" />
                <EnumTag v-else group="waste_status" value="pending" label="暂存待处置" />
              </template>
            </el-table-column>
            <el-table-column label="处置量" width="90" align="right">
              <template #default="{ row }">
                <span :class="{ 'pending-text': row.pending_quantity > 0 }">
                  {{ row.disposal_quantity === null ? '未处置' : formatNumber(row.disposal_quantity) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="vehicle_no" label="运输车辆" width="115">
              <template #default="{ row }">{{ row.vehicle_no || '-' }}</template>
            </el-table-column>
            <el-table-column prop="receiver" label="去向/接收单位" min-width="170" show-overflow-tooltip>
              <template #default="{ row }">{{ row.receiver || '-' }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <GreenSpaceFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { greenSpaceApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { formatArea, formatCurrency, formatDate, formatHours, formatNumber } from '@/utils/format'

import GreenSpaceFormDialog from './GreenSpaceFormDialog.vue'

const route = useRoute()
const router = useRouter()
const formDialog = ref(null)
const loading = ref(false)
const activeTab = ref('tasks')

const space = ref({})
const statistics = ref({
  task_status: {},
  record_count: 0,
  total_work_hours: 0,
  replacement_count: 0,
  replacement_quantity: 0,
  replacement_amount: 0,
  waste_count: 0,
  waste_produced_quantity: 0,
  waste_disposed_quantity: 0,
  waste_pending_quantity: 0,
})
const recentTasks = ref([])
const recentRecords = ref([])
const recentReplacements = ref([])
const recentWastes = ref([])
const replacementSummary = ref([])

const taskTotal = computed(() =>
  Object.values(statistics.value.task_status || {}).reduce((sum, value) => sum + value, 0),
)

async function load() {
  loading.value = true
  try {
    const data = await greenSpaceApi.profile(route.params.id)
    space.value = data.green_space || {}
    statistics.value = data.statistics || {}
    recentTasks.value = data.recent_tasks || []
    recentRecords.value = data.recent_records || []
    recentReplacements.value = data.recent_replacements || []
    recentWastes.value = data.recent_wastes || []
    replacementSummary.value = data.replacement_summary || []
  } finally {
    loading.value = false
  }
}

const LIST_ROUTES = {
  tasks: 'task-list',
  records: 'record-list',
  replacements: 'replacement-list',
  wastes: 'green-waste-list',
}

function goList(name) {
  router.push({ name: LIST_ROUTES[name], query: { green_space_id: route.params.id } })
}

onMounted(load)
</script>

<style scoped>
.tab-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.replacement-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.summary-tag {
  margin-right: 4px;
}

.pending-text {
  color: #e6a23c;
  font-weight: 600;
}
</style>
