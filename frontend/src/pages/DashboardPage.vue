<template>
  <div class="dashboard">
    <h2>仪表盘</h2>
    
    <!-- Stats Cards -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#409EFF"><Folder /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_projects }}</div>
              <div class="stat-label">项目总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#67C23A"><Search /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_scans }}</div>
              <div class="stat-label">扫描总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#F56C6C"><Warning /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_vulnerabilities }}</div>
              <div class="stat-label">漏洞总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon" color="#E6A23C"><CircleCheck /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.active_scans }}</div>
              <div class="stat-label">活跃扫描</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>漏洞严重性分布</span>
          </template>
          <div ref="severityChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>漏洞协议分布</span>
          </template>
          <div ref="protocolChart" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Vulnerabilities -->
    <el-card class="recent-card">
      <template #header>
        <span>最近发现的漏洞</span>
      </template>
      <el-table :data="recentVulnerabilities" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="漏洞标题" />
        <el-table-column prop="severity" label="严重性" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="protocol" label="协议" width="120" />
        <el-table-column prop="created_at" label="发现时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import api from '@/api/client'
import * as echarts from 'echarts'

const stats = reactive({
  total_projects: 0,
  total_scans: 0,
  total_vulnerabilities: 0,
  critical_vulnerabilities: 0,
  high_vulnerabilities: 0,
  active_scans: 0,
  recent_crashes: 0,
})

const recentVulnerabilities = ref([])

const severityChart = ref<HTMLElement>()
const protocolChart = ref<HTMLElement>()

const getSeverityType = (severity: string) => {
  const types: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'success',
    info: 'info',
  }
  return types[severity] || 'info'
}

const loadStats = async () => {
  try {
    const data = await api.get('/dashboard/stats')
    Object.assign(stats, data)
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

const loadRecentVulnerabilities = async () => {
  try {
    recentVulnerabilities.value = await api.get('/dashboard/vulnerabilities/recent')
  } catch (error) {
    console.error('Failed to load vulnerabilities:', error)
  }
}

const initCharts = async () => {
  if (!severityChart.value || !protocolChart.value) return

  // Severity distribution chart
  const severityData = await api.get('/dashboard/vulnerabilities/distribution/severity')
  const severityChartInstance = echarts.init(severityChart.value)
  severityChartInstance.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: severityData.map((d: any) => ({
        name: d.severity,
        value: d.count,
      })),
    }],
  })

  // Protocol distribution chart
  const protocolData = await api.get('/dashboard/vulnerabilities/distribution/protocol')
  const protocolChartInstance = echarts.init(protocolChart.value)
  protocolChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: protocolData.map((d: any) => d.protocol) },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: protocolData.map((d: any) => d.count),
    }],
  })
}

onMounted(async () => {
  await loadStats()
  await loadRecentVulnerabilities()
  await initCharts()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.stat-icon {
  font-size: 48px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.charts-row {
  margin-bottom: 20px;
}

.recent-card {
  margin-top: 20px;
}
</style>
