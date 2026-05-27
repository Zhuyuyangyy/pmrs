<template>
  <div class="scans-page">
    <h2>扫描记录</h2>
    
    <el-card>
      <el-table :data="scans" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="project_id" label="项目ID" width="100" />
        <el-table-column prop="scan_type" label="扫描类型" width="120" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)" />
          </template>
        </el-table-column>
        <el-table-column prop="total_testcases" label="测试用例" width="100" />
        <el-table-column prop="crashes_found" label="崩溃数" width="100">
          <template #default="{ row }">
            <span v-if="row.crashes_found > 0" style="color: #F56C6C;">{{ row.crashes_found }}</span>
            <span v-else>{{ row.crashes_found }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="开始时间" width="180" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" v-if="row.status === 'running'" type="danger" @click="cancelScan(row.id)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/client'

const scans = ref<any[]>([])
const loading = ref(false)

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info',
  }
  return types[status] || 'info'
}

const getProgressStatus = (status: string) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

const loadScans = async () => {
  loading.value = true
  try {
    scans.value = await api.get('/scans/')
  } catch (error) {
    ElMessage.error('加载扫描记录失败')
  } finally {
    loading.value = false
  }
}

const cancelScan = async (id: number) => {
  try {
    await api.post('/scans/' + id + '/cancel')
    ElMessage.success('扫描已取消')
    loadScans()
  } catch (error) {
    ElMessage.error('取消扫描失败')
  }
}

onMounted(loadScans)
</script>

<style scoped>
.scans-page {
  padding: 20px;
}
</style>
