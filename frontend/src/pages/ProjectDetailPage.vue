<template>
  <div class="project-detail-page">
    <h2>项目详情</h2>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <span>项目信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目名称">{{ project.name }}</el-descriptions-item>
            <el-descriptions-item label="协议">{{ project.protocol }}</el-descriptions-item>
            <el-descriptions-item label="目标IP">{{ project.target_ip }}</el-descriptions-item>
            <el-descriptions-item label="目标端口">{{ project.target_port }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(project.status)">{{ project.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ project.created_at }}</el-descriptions-item>
          </el-descriptions>
          
          <el-divider />
          
          <div class="actions">
            <el-button type="primary" @click="startScan" :loading="scanning">
              <el-icon><Search /></el-icon> 开始扫描
            </el-button>
          </div>
        </el-card>
        
        <el-card class="vulns-card" style="margin-top: 20px;">
          <template #header>
            <span>发现的漏洞</span>
          </template>
          <el-table :data="vulnerabilities" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="title" label="漏洞标题" />
            <el-table-column prop="severity" label="严重性" width="100">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cvss_base_score" label="CVSS" width="80" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="viewVulnerability(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="scans-card">
          <template #header>
            <span>扫描历史</span>
          </template>
          <el-timeline>
            <el-timeline-item v-for="scan in scans" :key="scan.id" :type="getScanType(scan.status)">
              <div class="scan-item">
                <div class="scan-time">{{ scan.created_at }}</div>
                <div class="scan-status">{{ scan.status }} - {{ scan.progress }}%</div>
                <div class="scan-crashes" v-if="scan.crashes_found > 0">
                  崩溃: {{ scan.crashes_found }}
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
    
    <el-dialog v-model="vulnDialogVisible" title="漏洞详情" width="600px">
      <div v-if="selectedVulnerability">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ selectedVulnerability.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedVulnerability.vulnerability_type }}</el-descriptions-item>
          <el-descriptions-item label="严重性">
            <el-tag :type="getSeverityType(selectedVulnerability.severity)">{{ selectedVulnerability.severity }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="CVSS评分">{{ selectedVulnerability.cvss_base_score }}</el-descriptions-item>
          <el-descriptions-item label="CVSS向量">{{ selectedVulnerability.cvss_vector }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <h4>描述</h4>
        <p>{{ selectedVulnerability.description }}</p>
        <h4 v-if="selectedVulnerability.poc_available">PoC</h4>
        <pre v-if="selectedVulnerability.poc_exploit">{{ selectedVulnerability.poc_exploit }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api/client'

const route = useRoute()
const projectId = route.params.id as string

const project = ref<any>({})
const vulnerabilities = ref<any[]>([])
const scans = ref<any[]>([])
const scanning = ref(false)
const vulnDialogVisible = ref(false)
const selectedVulnerability = ref<any>(null)

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info',
  }
  return types[status] || 'info'
}

const getSeverityType = (severity: string) => {
  const types: Record<string, string> = {
    critical: 'danger', high: 'warning', medium: 'info', low: 'success', info: 'info',
  }
  return types[severity] || 'info'
}

const getScanType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info', running: 'primary', completed: 'success', failed: 'danger', cancelled: 'info',
  }
  return types[status] || 'info'
}

const loadProject = async () => {
  try {
    project.value = await api.get('/projects/' + projectId)
  } catch (error) {
    ElMessage.error('加载项目失败')
  }
}

const loadVulnerabilities = async () => {
  try {
    vulnerabilities.value = await api.get('/vulnerabilities/', { project_id: projectId })
  } catch (error) {
    console.error('Failed to load vulnerabilities:', error)
  }
}

const loadScans = async () => {
  try {
    scans.value = await api.get('/scans/', { project_id: projectId })
  } catch (error) {
    console.error('Failed to load scans:', error)
  }
}

const startScan = async () => {
  try {
    scanning.value = true
    await api.post('/scans/', { project_id: projectId, scan_type: 'full' })
    ElMessage.success('扫描已启动')
    setTimeout(loadScans, 1000)
  } catch (error) {
    ElMessage.error('启动扫描失败')
  } finally {
    scanning.value = false
  }
}

const viewVulnerability = (vuln: any) => {
  selectedVulnerability.value = vuln
  vulnDialogVisible.value = true
}

onMounted(() => {
  loadProject()
  loadVulnerabilities()
  loadScans()
})
</script>

<style scoped>
.project-detail-page {
  padding: 20px;
}

.scan-item {
  line-height: 1.6;
}

.scan-time {
  font-size: 12px;
  color: #999;
}

.scan-status {
  font-weight: 500;
}

.scan-crashes {
  color: #F56C6C;
  font-size: 12px;
}
</style>
