<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑废弃物处置记录 · ${form.waste_no}` : '登记废弃物处置记录'"
             width="780px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <div class="section-title">产生信息</div>
      <el-form-item label="来源绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset"
                          @update:model-value="onGreenSpaceChange" />
      </el-form-item>
      <el-form-item label="关联养护记录" :error="fieldErrors.maintenance_record_id">
        <RecordSelect v-model="form.maintenance_record_id" :green-space-id="form.green_space_id"
                      :preset="recordPreset" />
        <div class="form-hint">如废弃物来自某次修剪、除草作业，可关联对应养护记录（选填）。</div>
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="废弃物类型" prop="waste_type" :error="fieldErrors.waste_type">
            <el-select v-model="form.waste_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="产生日期" prop="produce_date" :error="fieldErrors.produce_date">
            <el-date-picker v-model="form.produce_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="产生数量" prop="quantity" :error="fieldErrors.quantity">
            <el-input-number v-model="form.quantity" :min="0.01" :max="999999" :precision="2"
                             :controls="false" placeholder="请输入数量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量单位" :error="fieldErrors.unit">
            <el-select v-model="form.unit" style="width: 100%">
              <el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="产生环节" :error="fieldErrors.source_detail">
        <el-input v-model="form.source_detail" placeholder="如：行道树整形修剪枝条" maxlength="128" />
      </el-form-item>

      <div class="section-title disposal-title">
        处置信息
        <el-switch v-model="hasDisposal" inline-prompt active-text="已处置" inactive-text="暂存待处置"
                   class="disposal-switch" @change="onDisposalToggle" />
      </div>
      <template v-if="hasDisposal">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="处置方式" prop="disposal_method" :error="fieldErrors.disposal_method">
              <el-select v-model="form.disposal_method" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="处置日期" prop="disposal_date" :error="fieldErrors.disposal_date">
              <el-date-picker v-model="form.disposal_date" type="date" value-format="YYYY-MM-DD"
                              placeholder="选择日期" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="处置数量" :error="fieldErrors.disposal_quantity">
              <el-input-number v-model="form.disposal_quantity" :min="0" :max="form.quantity || 999999"
                               :precision="2" :controls="false" style="width: 100%"
                               placeholder="留空表示全部处置" />
              <div class="form-hint">留空按产生量全部处置；{{ pendingHint }}</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="运输车辆" :error="fieldErrors.vehicle_no">
              <el-input v-model="form.vehicle_no" placeholder="如：浙A·3K21挂（粉碎还田可留空）" maxlength="32" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="接收/去向单位" :error="fieldErrors.receiver">
          <el-input v-model="form.receiver" placeholder="如：余杭区园林废弃物资源化利用中心 / 就地处置" maxlength="96" />
        </el-form-item>
        <el-form-item label="去向说明" :error="fieldErrors.disposal_note">
          <el-input v-model="form.disposal_note" type="textarea" :rows="2" maxlength="255"
                    placeholder="如：粉碎发酵后加工为栽培基质；或运至消纳场填埋覆土" />
        </el-form-item>
      </template>

      <el-form-item label="登记人" :error="fieldErrors.operator">
        <el-input v-model="form.operator" maxlength="64" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { greenWasteApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import RecordSelect from '@/components/common/RecordSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('green_waste_type')
const { options: unitOptions } = useEnumOptions('green_waste_unit')
const { options: methodOptions } = useEnumOptions('disposal_method')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const recordPreset = ref(null)
const hasDisposal = ref(false)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const pendingHint = computed(() => {
  const produced = Number(form.quantity || 0)
  const disposed = form.disposal_quantity === null || form.disposal_quantity === undefined || form.disposal_quantity === ''
    ? produced
    : Number(form.disposal_quantity || 0)
  const pending = Math.max(produced - disposed, 0)
  return pending > 0 ? `本次处置后仍有 ${pending} 暂存待处置` : '处置后无待处置差异'
})

const rules = {
  green_space_id: [{ required: true, message: '请选择来源绿地', trigger: 'change' }],
  waste_type: [{ required: true, message: '请选择废弃物类型', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入产生数量', trigger: 'blur' }],
  produce_date: [{ required: true, message: '请选择产生日期', trigger: 'change' }],
  disposal_method: [{ required: true, message: '请选择处置方式', trigger: 'change' }],
  disposal_date: [{ required: true, message: '请选择处置日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    waste_no: '',
    green_space_id: null,
    maintenance_record_id: null,
    waste_type: 'branch',
    quantity: null,
    unit: 'ton',
    produce_date: today(),
    source_detail: '',
    operator: '',
    disposal_method: '',
    disposal_quantity: null,
    disposal_date: '',
    vehicle_no: '',
    receiver: '',
    disposal_note: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  recordPreset.value = null
  editingId.value = row?.id ?? null
  hasDisposal.value = false
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    hasDisposal.value = row.status === 'disposed'
    if (row.disposal_method) form.disposal_method = row.disposal_method
    if (row.disposal_date) form.disposal_date = row.disposal_date
    spacePreset.value = row.green_space || null
    recordPreset.value = row.record ? { ...row.record, id: row.maintenance_record_id } : null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

function onGreenSpaceChange() {
  form.maintenance_record_id = null
  recordPreset.value = null
}

function onDisposalToggle(active) {
  if (!active) {
    form.disposal_method = ''
    form.disposal_quantity = null
    form.disposal_date = ''
    form.vehicle_no = ''
    form.receiver = ''
    form.disposal_note = ''
    fieldErrors.value = {}
  } else if (!form.disposal_date) {
    form.disposal_date = form.produce_date || today()
  }
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  if (!payload.waste_no) delete payload.waste_no
  if (!payload.maintenance_record_id) payload.maintenance_record_id = null
  if (!hasDisposal.value) {
    // 暂存待处置：清空处置字段
    payload.disposal_method = null
    payload.disposal_quantity = null
    payload.disposal_date = null
    payload.vehicle_no = null
    payload.receiver = null
    payload.disposal_note = null
  } else {
    if (!payload.disposal_quantity) payload.disposal_quantity = null
  }
  try {
    if (isEdit.value) {
      await greenWasteApi.update(editingId.value, payload)
      ElMessage.success('废弃物处置记录已更新')
    } else {
      await greenWasteApi.create(payload)
      ElMessage.success('废弃物处置记录登记成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 4px 0 16px;
  padding-left: 10px;
  border-left: 3px solid var(--gs-primary, #48a17a);
}

.disposal-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.disposal-switch {
  margin-left: 4px;
}

.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}
</style>
