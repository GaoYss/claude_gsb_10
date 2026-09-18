<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑废弃物处置记录 · ${form.record_no}` : '登记废弃物处置记录'"
             width="720px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="来源绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" />
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
          <el-form-item label="产生日期" prop="generate_date" :error="fieldErrors.generate_date">
            <el-date-picker v-model="form.generate_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="产生量" prop="quantity" :error="fieldErrors.quantity">
            <el-input-number v-model="form.quantity" :min="0.01" :max="999999" :precision="2"
                             :controls="false" placeholder="请输入产生量" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计量单位" :error="fieldErrors.unit">
            <el-select v-model="form.unit" style="width: 100%">
              <el-option v-for="item in unitOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="处置方式" prop="disposal_method" :error="fieldErrors.disposal_method">
            <el-select v-model="form.disposal_method" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="处置量" :error="fieldErrors.disposed_quantity">
            <el-input-number v-model="form.disposed_quantity" :min="0" :max="form.quantity ?? 999999"
                             :precision="2" :controls="false" placeholder="未处置填 0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="处置日期" :error="fieldErrors.disposed_date">
            <el-date-picker v-model="form.disposed_date" type="date" value-format="YYYY-MM-DD"
                            :disabled-date="beforeGenerateDate" placeholder="不早于产生日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="运输车辆" :prop="isTransport ? 'transport_vehicle' : ''"
                        :error="fieldErrors.transport_vehicle">
            <el-input v-model="form.transport_vehicle" placeholder="如：浙A3D567" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="去向" :prop="isTransport ? 'destination' : ''" :error="fieldErrors.destination">
            <el-input v-model="form.destination" placeholder="消纳场 / 利用企业 / 还田地点" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="登记人" :error="fieldErrors.operator">
            <el-input v-model="form.operator" maxlength="64" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item v-if="remaining > 0">
        <el-alert type="warning" :closable="false" show-icon
                  :title="`当前待处置 ${remaining} ${unitLabel}，保存后将计入月度对账差额`" />
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

import { wasteRecordApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('waste_type')
const { options: methodOptions } = useEnumOptions('waste_disposal_method')
const { options: unitOptions, label: unitLabelOf } = useEnumOptions('waste_unit')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)
const isTransport = computed(() => form.disposal_method === 'transport')

const remaining = computed(() => {
  const value = Number(form.quantity || 0) - Number(form.disposed_quantity || 0)
  return Math.round(value * 100) / 100
})
const unitLabel = computed(() => unitLabelOf(form.unit) || '')

const rules = computed(() => ({
  green_space_id: [{ required: true, message: '请选择来源绿地', trigger: 'change' }],
  waste_type: [{ required: true, message: '请选择废弃物类型', trigger: 'change' }],
  generate_date: [{ required: true, message: '请选择产生日期', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入产生量', trigger: 'blur' }],
  disposal_method: [{ required: true, message: '请选择处置方式', trigger: 'change' }],
  transport_vehicle: isTransport.value
    ? [{ required: true, message: '外运消纳时需填写运输车辆', trigger: 'blur' }]
    : [],
  destination: isTransport.value
    ? [{ required: true, message: '外运消纳时需填写去向', trigger: 'blur' }]
    : [],
}))

function emptyForm() {
  return {
    record_no: '',
    green_space_id: null,
    waste_type: 'branch',
    generate_date: today(),
    quantity: null,
    unit: 'ton',
    disposal_method: 'mulch',
    disposed_quantity: 0,
    disposed_date: '',
    transport_vehicle: '',
    destination: '',
    operator: '',
    remark: '',
  }
}

function beforeGenerateDate(day) {
  if (!form.generate_date) return false
  return day < new Date(`${form.generate_date}T00:00:00`)
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    spacePreset.value = row.green_space || null
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = { ...form }
  delete payload.record_no
  if (!payload.disposed_date) payload.disposed_date = null
  if (!payload.transport_vehicle) payload.transport_vehicle = null
  if (!payload.destination) payload.destination = null
  try {
    if (isEdit.value) {
      await wasteRecordApi.update(editingId.value, payload)
      ElMessage.success('废弃物处置记录已更新')
    } else {
      await wasteRecordApi.create(payload)
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
