<template>
  <div class="page">
    <PageHeader title="废弃物处置台账" description="登记修剪、除草等绿化废弃物的产生与处置去向，按月度与绿地核算产生量、处置量及待处置差异">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记废弃物</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 车辆 / 去向 / 产生环节" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 200px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按来源绿地筛选"
                            @update:model-value="search" />
        </div>
        <el-select v-model="filters.waste_type" placeholder="废弃物类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.disposal_method" placeholder="处置方式" clearable @change="search">
          <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" placeholder="处置状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="filters.month" type="month" value-format="YYYY-MM"
                        placeholder="产生月份" clearable @change="search" style="width: 140px" />
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="产生日期起" end-placeholder="产生日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="产生量合计" :value="formatNumber(summary?.total_quantity ?? 0)"
                :hint="`共 ${formatNumber(summary?.total_count ?? 0)} 条记录`" icon="Files" />
      <StatCard label="处置量合计" :value="formatNumber(summary?.total_disposed_quantity ?? 0)"
                hint="粉碎还田 + 外运消纳 + 资源利用" tone="info" icon="Van" />
      <StatCard label="待处置差异" :value="formatNumber(summary?.total_pending_quantity ?? 0)"
                :hint="`${formatNumber(summary?.pending_count ?? 0)} 条记录尚未补录处置`"
                tone="warning" icon="Warning" />
      <StatCard label="涉及绿地" :value="formatNumber(summary?.by_green_space?.length ?? 0)" unit="处"
                :hint="`${unbalancedSpaceCount} 处绿地产生量与处置量不一致`" icon="MapLocation" />
    </div>

    <el-alert
      v-if="unbalancedSpaces.length"
      class="balance-alert"
      type="warning"
      :closable="false"
      show-icon
      title="产生量与处置量对不上的提示"
    >
      <template #default>
        <div v-for="item in unbalancedSpaces" :key="item.green_space_id" class="balance-line">
          <el-tag size="small" type="warning" effect="plain">{{ item.green_space_name }}</el-tag>
          <span>产生 {{ formatNumber(item.produced) }}，已处置 {{ formatNumber(item.disposed) }}，
            尚有 <b>{{ formatNumber(item.pending) }}</b> 暂存待处置</span>
        </div>
        <div v-if="unbalancedMonths.length" class="balance-line balance-months">
          <span>差异涉及月份：{{ unbalancedMonths.map((m) => `${m.month}（待处置 ${formatNumber(m.pending)}）`).join('、') }}</span>
        </div>
      </template>
    </el-alert>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条记录，产生量合计
          <strong>{{ formatNumber(summary?.total_quantity ?? 0) }}</strong>，处置量合计
          <strong>{{ formatNumber(summary?.total_disposed_quantity ?? 0) }}</strong>，待处置
          <strong class="pending-text">{{ formatNumber(summary?.total_pending_quantity ?? 0) }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>产生环节：</b>{{ row.source_detail || '-' }}</span>
              <span><b>运输车辆：</b>{{ row.vehicle_no || '-' }}</span>
              <span><b>接收/去向单位：</b>{{ row.receiver || '-' }}</span>
              <span><b>去向说明：</b>{{ row.disposal_note || '-' }}</span>
              <span><b>登记人：</b>{{ row.operator || '-' }}</span>
              <span><b>关联养护记录：</b>{{ row.record ? `${row.record.record_no}（${formatDate(row.record.record_date)}）` : '未关联' }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="waste_no" label="编号" width="150" />
        <el-table-column label="来源绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="类型" width="115">
          <template #default="{ row }">
            <EnumTag group="green_waste_type" :value="row.waste_type" :label="row.waste_type_label" />
          </template>
        </el-table-column>
        <el-table-column label="产生量" width="100" align="right">
          <template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit_label }}</template>
        </el-table-column>
        <el-table-column prop="produce_date" label="产生日期" width="100" />
        <el-table-column label="处置方式" width="110">
          <template #default="{ row }">
            <EnumTag v-if="row.disposal_method" group="disposal_method"
                     :value="row.disposal_method" :label="row.disposal_method_label" />
            <EnumTag v-else group="waste_status" value="pending" label="暂存待处置" />
          </template>
        </el-table-column>
        <el-table-column label="处置量" width="100" align="right">
          <template #default="{ row }">
            <span :class="{ 'pending-text': row.disposal_quantity === null }">
              {{ row.disposal_quantity === null ? '未处置' : formatNumber(row.disposal_quantity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="运输车辆" width="120">
          <template #default="{ row }">{{ row.vehicle_no || '-' }}</template>
        </el-table-column>
        <el-table-column label="去向/接收单位" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.receiver || '-' }}</template>
        </el-table-column>
        <el-table-column prop="disposal_date" label="处置日期" width="100" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <div class="summary-grid">
      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">按月份汇总</span>
          <span class="summary-text">按产生月份统计（当前筛选条件）</span>
        </div>
        <el-table :data="summary?.by_month || []" size="small" border empty-text="暂无数据"
                  :row-class-name="monthRowClass">
          <el-table-column prop="month" label="月份" width="110" />
          <el-table-column label="产生量" width="110" align="right">
            <template #default="{ row }">{{ formatNumber(row.produced) }}</template>
          </el-table-column>
          <el-table-column label="处置量" width="110" align="right">
            <template #default="{ row }">{{ formatNumber(row.disposed) }}</template>
          </el-table-column>
          <el-table-column label="待处置差异" min-width="200">
            <template #default="{ row }">
              <span :class="{ 'pending-text': row.pending > 0 }">{{ formatNumber(row.pending) }}</span>
              <el-tag v-if="row.pending > 0" size="small" type="warning" effect="plain" class="gap-tag">
                处置不完整
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="panel">
        <div class="table-toolbar">
          <span class="panel-title">按绿地汇总</span>
          <span class="summary-text">差异按待处置量降序</span>
        </div>
        <el-table :data="summary?.by_green_space || []" size="small" border empty-text="暂无数据">
          <el-table-column label="来源绿地" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.green_space_name }}</template>
          </el-table-column>
          <el-table-column prop="district" label="行政区" width="90" />
          <el-table-column label="产生量" width="90" align="right">
            <template #default="{ row }">{{ formatNumber(row.produced) }}</template>
          </el-table-column>
          <el-table-column label="处置量" width="90" align="right">
            <template #default="{ row }">{{ formatNumber(row.disposed) }}</template>
          </el-table-column>
          <el-table-column label="待处置差异" width="110" align="right">
            <template #default="{ row }">
              <span :class="{ 'pending-text': row.pending > 0 }">{{ formatNumber(row.pending) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="panel-title">处置方式构成</span>
        <span class="summary-text">含暂存待处置一组</span>
      </div>
      <el-table :data="summary?.by_method || []" size="small" border empty-text="暂无数据">
        <el-table-column prop="label" label="处置方式" width="160" />
        <el-table-column prop="count" label="记录条数" width="110" />
        <el-table-column label="处置量" width="130" align="right">
          <template #default="{ row }">{{ formatNumber(row.disposed) }}</template>
        </el-table-column>
        <el-table-column label="占比" min-width="220">
          <template #default="{ row }">
            <el-progress :percentage="methodShare(row)" :stroke-width="12"
                         :color="row.value === null ? '#e6a23c' : '#48a17a'"
                         :format="() => `${methodShare(row)}%`" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <WasteFormDialog ref="formDialog" @saved="load" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { greenWasteApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatDate, formatDateTime, formatNumber } from '@/utils/format'

import WasteFormDialog from './WasteFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])

const { options: typeOptions } = useEnumOptions('green_waste_type')
const { options: methodOptions } = useEnumOptions('disposal_method')
const { options: statusOptions } = useEnumOptions('waste_status')

const { filters, meta, items, summary, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(greenWasteApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      waste_type: '',
      disposal_method: '',
      status: '',
      month: '',
      date_from: '',
      date_to: '',
    },
  })

const unbalancedSpaces = computed(() => summary.value?.unbalanced?.green_spaces || [])
const unbalancedMonths = computed(() => summary.value?.unbalanced?.months || [])
const unbalancedSpaceCount = computed(() => unbalancedSpaces.value.length)

function monthRowClass({ row }) {
  return row.pending > 0 ? 'row-pending' : ''
}

function methodShare(row) {
  const total = summary.value?.total_disposed_quantity || 0
  if (!total) return 0
  return Math.round((Number(row.disposed) / total) * 1000) / 10
}

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除废弃物处置记录「${row.waste_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await greenWasteApi.remove(row.id)
    ElMessage.success('废弃物处置记录已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.panel-title {
  font-weight: 600;
}

.pending-text {
  color: #e6a23c;
  font-weight: 600;
}

.balance-alert {
  margin-bottom: 16px;
}

.balance-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  line-height: 1.9;
}

.balance-months {
  color: #606266;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 16px;
}

.gap-tag {
  margin-left: 8px;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}

:deep(.el-table .row-pending) {
  background-color: #fdf6ec;
}

@media (max-width: 1200px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
