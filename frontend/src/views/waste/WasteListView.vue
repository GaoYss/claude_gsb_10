<template>
  <div class="page">
    <PageHeader title="废弃物处置台账" description="登记修剪与清理废弃物的产生、运输与去向，按月份与绿地对账">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记处置记录</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="编号 / 车辆 / 去向 / 登记人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <div style="width: 220px">
          <GreenSpaceSelect v-model="filters.green_space_id" placeholder="按绿地筛选" @update:model-value="search" />
        </div>
        <el-select v-model="filters.waste_type" placeholder="废弃物类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.disposal_method" placeholder="处置方式" clearable @change="search">
          <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="产生日期起" end-placeholder="产生日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="reset">重置</el-button>
      </div>
    </div>

    <div class="stat-grid">
      <StatCard label="处置记录" :value="formatNumber(summary?.total_count ?? 0)" unit="条"
                hint="按当前筛选条件统计" icon="Van" />
      <StatCard label="产生量" :value="unitAmountText('generated')" hint="按计量单位分别合计"
                tone="info" icon="Collection" />
      <StatCard label="处置量" :value="unitAmountText('disposed')" hint="粉碎还田 / 外运消纳 / 资源利用"
                icon="Finished" />
      <StatCard label="待处置量" :value="unitAmountText('remaining')" :tone="hasRemaining ? 'warning' : 'default'"
                :hint="hasRemaining ? '产生量与处置量存在差额' : '产生量与处置量一致'" icon="Warning" />
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 条处置记录，
          待处置 <strong>{{ unitAmountText('remaining') }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="reloadAll">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-detail">
              <span><b>处置日期：</b>{{ row.disposed_date || '未处置' }}</span>
              <span><b>登记人：</b>{{ row.operator || '-' }}</span>
              <span><b>登记时间：</b>{{ formatDateTime(row.created_at) }}</span>
              <span><b>最近更新：</b>{{ formatDateTime(row.updated_at) }}</span>
              <span v-if="row.remark"><b>备注：</b>{{ row.remark }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="record_no" label="编号" width="150" />
        <el-table-column label="来源绿地" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="废弃物类型" width="110">
          <template #default="{ row }">
            <EnumTag group="waste_type" :value="row.waste_type" :label="row.waste_type_label" />
          </template>
        </el-table-column>
        <el-table-column prop="generate_date" label="产生日期" width="105" />
        <el-table-column label="产生量" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit_label }}</template>
        </el-table-column>
        <el-table-column label="处置方式" width="105">
          <template #default="{ row }">
            <EnumTag group="waste_disposal_method" :value="row.disposal_method" :label="row.disposal_method_label" />
          </template>
        </el-table-column>
        <el-table-column label="处置量" width="110" align="right">
          <template #default="{ row }">{{ formatNumber(row.disposed_quantity) }} {{ row.unit_label }}</template>
        </el-table-column>
        <el-table-column label="待处置" width="100" align="right">
          <template #default="{ row }">
            <span :class="{ 'remaining-gap': row.remaining_quantity > 0 }">
              {{ formatNumber(row.remaining_quantity) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="95">
          <template #default="{ row }">
            <el-tag :type="statusTag[row.disposal_status]?.type" size="small" disable-transitions>
              {{ statusTag[row.disposal_status]?.text || row.disposal_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="运输车辆" width="110">
          <template #default="{ row }">{{ row.transport_vehicle || '-' }}</template>
        </el-table-column>
        <el-table-column label="去向" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.destination || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
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

    <div v-if="monthly?.mismatches?.length" class="panel">
      <el-alert type="warning" show-icon :closable="false"
                :title="`以下 ${monthly.mismatches.length} 个「月份 × 绿地」产生量与处置量对不上，请核实补登`" />
      <ul class="mismatch-list">
        <li v-for="row in monthly.mismatches" :key="`${row.month}-${row.green_space_id}-${row.unit}`">
          <span class="mismatch-month">{{ row.month }}</span>
          <span class="mismatch-space">{{ row.green_space?.name || `绿地 #${row.green_space_id}` }}</span>
          <span>
            产生 <b>{{ formatNumber(row.generated) }}</b> {{ row.unit_label }}，
            处置 <b>{{ formatNumber(row.disposed) }}</b> {{ row.unit_label }}，
            差额 <b class="remaining-gap">{{ formatNumber(row.remaining) }}</b> {{ row.unit_label }}
          </span>
        </li>
      </ul>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="panel-title">月度对账汇总</span>
        <span class="summary-text">按产生月份 × 绿地 × 计量单位汇总，与当前筛选条件联动</span>
      </div>
      <el-table :data="monthly?.rows || []" v-loading="monthlyLoading" size="small" border empty-text="暂无数据">
        <el-table-column prop="month" label="月份" width="100" />
        <el-table-column label="绿地" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">{{ row.green_space?.name || `绿地 #${row.green_space_id}` }}</template>
        </el-table-column>
        <el-table-column prop="unit_label" label="单位" width="80" />
        <el-table-column label="产生量" width="120" align="right">
          <template #default="{ row }">{{ formatNumber(row.generated) }}</template>
        </el-table-column>
        <el-table-column label="处置量" width="120" align="right">
          <template #default="{ row }">{{ formatNumber(row.disposed) }}</template>
        </el-table-column>
        <el-table-column label="差额" width="120" align="right">
          <template #default="{ row }">
            <span :class="{ 'remaining-gap': row.remaining !== 0 }">{{ formatNumber(row.remaining) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="对账状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_mismatched ? 'danger' : 'success'" size="small" disable-transitions>
              {{ row.is_mismatched ? '有差额' : '平账' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="panel-title">处置方式汇总</span>
        <span class="summary-text">按当前筛选条件统计</span>
      </div>
      <el-table :data="summary?.by_method || []" size="small" border empty-text="暂无数据">
        <el-table-column prop="label" label="处置方式" width="140" />
        <el-table-column prop="count" label="记录条数" width="110" />
        <el-table-column label="产生量" width="140">
          <template #default="{ row }">{{ formatNumber(row.generated) }}</template>
        </el-table-column>
        <el-table-column label="处置量" width="140">
          <template #default="{ row }">{{ formatNumber(row.disposed) }}</template>
        </el-table-column>
        <el-table-column label="占比" min-width="200">
          <template #default="{ row }">
            <el-progress :percentage="shareOf(row.count)" :stroke-width="12"
                         :color="'#48a17a'" :format="() => `${shareOf(row.count)}%`" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <WasteFormDialog ref="formDialog" @saved="reloadAll" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { wasteRecordApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { formatDateTime, formatNumber } from '@/utils/format'

import WasteFormDialog from './WasteFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])

const { options: typeOptions } = useEnumOptions('waste_type')
const { options: methodOptions } = useEnumOptions('waste_disposal_method')

const { filters, meta, items, summary, loading, load, search: searchList, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(wasteRecordApi.list, {
    initialFilters: {
      keyword: '',
      green_space_id: route.query.green_space_id ? Number(route.query.green_space_id) : null,
      waste_type: '',
      disposal_method: '',
      date_from: '',
      date_to: '',
    },
  })

const statusTag = {
  pending: { text: '未处置', type: 'info' },
  partial: { text: '部分处置', type: 'warning' },
  cleared: { text: '已处置清', type: 'success' },
}

const monthly = ref(null)
const monthlyLoading = ref(false)

const hasRemaining = computed(() =>
  (summary.value?.by_unit || []).some((row) => row.remaining > 0)
)

/** 分单位数量拼接，如「3.5 吨 · 6 立方米」。 */
function unitAmountText(key) {
  const rows = (summary.value?.by_unit || []).filter((row) => row[key] > 0)
  if (!rows.length) return '0'
  return rows.map((row) => `${formatNumber(row[key])} ${row.unit_label}`).join(' · ')
}

function shareOf(count) {
  const total = summary.value?.total_count || 0
  if (!total) return 0
  return Math.round((Number(count) / total) * 1000) / 10
}

async function loadMonthly() {
  monthlyLoading.value = true
  try {
    monthly.value = await wasteRecordApi.monthly({
      green_space_id: filters.green_space_id || undefined,
      waste_type: filters.waste_type || undefined,
      disposal_method: filters.disposal_method || undefined,
      date_from: filters.date_from || undefined,
      date_to: filters.date_to || undefined,
    })
  } catch {
    monthly.value = null
  } finally {
    monthlyLoading.value = false
  }
}

function search() {
  loadMonthly()
  return searchList()
}

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

function reset() {
  dateRange.value = []
  resetFilters()
  loadMonthly()
}

function reloadAll() {
  loadMonthly()
  return load()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除处置记录「${row.record_no}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await wasteRecordApi.remove(row.id)
    ElMessage.success('废弃物处置记录已删除')
    await reloadAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

onMounted(loadMonthly)
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.panel-title {
  font-weight: 600;
}

.remaining-gap {
  color: #f56c6c;
  font-weight: 600;
}

.expand-detail {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 6px 16px;
  padding: 4px 12px;
  color: #606266;
  font-size: 13px;
}

.mismatch-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #606266;
  font-size: 13px;
}

.mismatch-list li {
  display: flex;
  gap: 12px;
  align-items: baseline;
}

.mismatch-month {
  font-weight: 600;
  color: #303133;
}

.mismatch-space {
  color: #303133;
}
</style>
