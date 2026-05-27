<template>
  <div class="new-project-page">
    <h2>新建项目</h2>
    
    <el-card>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        
        <el-form-item label="项目描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="3" placeholder="请输入项目描述" />
        </el-form-item>
        
        <el-form-item label="目标IP" prop="target_ip">
          <el-input v-model="form.target_ip" placeholder="如: 192.168.1.100" />
        </el-form-item>
        
        <el-form-item label="目标端口" prop="target_port">
          <el-input-number v-model="form.target_port" :min="1" :max="65535" />
        </el-form-item>
        
        <el-form-item label="协议类型" prop="protocol">
          <el-select v-model="form.protocol" placeholder="请选择协议">
            <el-option label="Modbus TCP" value="modbus_tcp" />
            <el-option label="IEC 61850" value="iec61850" />
            <el-option label="DNP3" value="dnp3" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">创建项目</el-button>
          <el-button @click=".back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import api from '@/api/client'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  target_ip: '127.0.0.1',
  target_port: 502,
  protocol: 'modbus_tcp',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  target_ip: [
    { required: true, message: '请输入目标IP', trigger: 'blur' },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'IP格式不正确', trigger: 'blur' },
  ],
  target_port: [{ required: true, message: '请输入目标端口', trigger: 'blur' }],
  protocol: [{ required: true, message: '请选择协议类型', trigger: 'change' }],
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    submitting.value = true
    
    const project = await api.post('/projects/', form)
    ElMessage.success('项目创建成功')
    router.push()
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.new-project-page {
  padding: 20px;
  max-width: 600px;
}
</style>
