<template>
  <div class="vulnerabilities-page">
    <h2>漏洞管理</h2>
    
    <el-card>
      <template #header>
        <div class="card-header">
          <span>漏洞列表</span>
          <div class="filters">
            <el-select v-model="filterSeverity" placeholder="严重性" clearable style="width: 120px; margin-right: 10px;">
              <el-option label="Critical" value="critical" />
              <el-option label="High" value="high" />
              <el-option label="Medium" value="medium" />
              <el-option label="Low" value="low" />
              <el-option label="Info" value="info" />
            </el-select>
            <el-select v-model="filterProtocol" placeholder="协议" clearable style="width: 120px;">
              <el-option label="Modbus TCP" value="modbus_tcp" />
              <el-option label="IEC 61850" value="iec61850" />
              <el-option label="DNP3" value="dnp3" />
            </el-select>
          </div>
        </div>
      </template>
      
      <el-table :data="vulnerabilities" stripe v-loading="loading" @row-click="viewDetail">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="漏洞标题" />
        <el-table-column prop="vulnerability_type" label="类型" width="150" />
        <el-table-column prop="severity" label="严重性" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="protocol" label="协议" width="120" />
        <el-table-column prop="cvss_base_score" label="CVSS" width="80" />
        <el-table-column prop="created_at" label="发现时间" width="180" />
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadVulnerabilities"
        style="margin-top: 20px;"
      />
    </el-card>
    
    <el-dialog v-model="dialogVisible" title="漏洞详情" width="700px">
      <div v-if="selectedVulnerability">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedVulnerability.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedVulnerability.vulnerability_type }}</el-descriptions-item>
          <el-descriptions-item label="协议">{{ selectedVulnerability.protocol }}</el-descriptions-item>
          <el-descriptions-item label="严重性">
            <el-tag :type="getSeverityType(selectedVulnerability.severity)">{{ selectedVulnerability.severity }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="CVSS评分">{{ selectedVulnerability.cvss_base_score }}</el-descriptions-item>
          <el-descriptions-item label="CVSS向量">{{ selectedVulnerability.cvss_vector }}</el-descriptions-item>
          <el-descriptions-item label="位置">{{ selectedVulnerability.location }}</el-descriptions-item>
        </el-descriptions>
        
        <el-divider />
        <h4>描述</h4>
        <p>{{ selectedVulnerability.description }}</p>
        
        <h4>修复建议</h4>
        <p>{{ selectedVulnerability.remediation }}</p>
        
        <template v-if="selectedVulnerability.poc_available">
          <el-divider />
          <h4>PoC代码</h4>
          <pre class="poc-code">{{ selectedVulnerability.poc_exploit }}</pre>
        </template>
        
        <el-divider />
        <div class="dialog-footer">
          <el-button @click="markFalsePositive" v-if="!selectedVulnerability.is_false_positive">标记为误报</el-button>
          <el-button type="primary" @click="confirmVulnerability">确认漏洞</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/client'

const vulnerabilities = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const selectedVulnerability = ref<any>(null)
const filterSeverity = ref('')
const filterProtocol = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const getSeverityType = (severity: string) => {
  const types: Record<string, string> = {
    critical: 'danger', high: 'warning', medium: 'info', low: 'success', info: 'info',
  }
  return types[severity] || 'info'
}

const loadVulnerabilities = async () => {
  loading.value = true
  try {
    const params: any = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterSeverity.value) params.severity = filterSeverity.value
    if (filterProtocol.value) params.protocol = filterProtocol.value
    
    const response = await api.get('/vulnerabilities/', params)
    vulnerabilities.value = Array.isArray(response) ? response : []
    total.value = response.total || vulnerabilities.value.length
  } catch (error) {
    console.error('Failed to load vulnerabilities:', error)
  } finally {
    loading.value = false
  }
}

const viewDetail = (row: any) => {
  selectedVulnerability.value = row
  dialogVisible.value = true
}

const confirmVulnerability = async () => {
  try {
    await api.patch('/vulnerabilities/' + selectedVulnerability.value.id + '/confirm')
    ElMessage.success('漏洞已确认')
    dialogVisible.value = false
    loadVulnerabilities()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const markFalsePositive = async () => {
  try {
    await api.patch('/vulnerabilities/' + selectedVulnerability.value.id + '/confirm', { is_false_positive: true })
    ElMessage.success('已标记为误报')
    dialogVisible.value = false
    loadVulnerabilities()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(loadVulnerabilities)
</script>

<style scoped>
.vulnerabilities-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
}

.poc-code {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
}

.dialog-footer {
  text-align: right;
}
</style>
