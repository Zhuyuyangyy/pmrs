<template>
  <div class="protocols-page">
    <h2>协议分析</h2>
    
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>支持的协议</span>
          </template>
          <el-list>
            <el-list-item v-for="protocol in protocols" :key="protocol.name">
              <div class="protocol-item">
                <el-tag size="large">{{ protocol.name }}</el-tag>
                <span class="protocol-port">端口: {{ protocol.default_port }}</span>
              </div>
            </el-list-item>
          </el-list>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>协议数据包解析</span>
          </template>
          <el-form :inline="true">
            <el-form-item label="协议">
              <el-select v-model="selectedProtocol" style="width: 150px;">
                <el-option label="Modbus TCP" value="modbus_tcp" />
                <el-option label="IEC 61850" value="iec61850" />
                <el-option label="DNP3" value="dnp3" />
              </el-select>
            </el-form-item>
            <el-form-item label="十六进制数据">
              <el-input v-model="packetData" placeholder="如: 00000000000601030000000A" style="width: 300px;" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="parsePacket">解析</el-button>
            </el-form-item>
          </el-form>
          
          <div v-if="parseResult" class="parse-result">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="有效性">
                <el-tag :type="parseResult.valid ? 'success' : 'danger'">
                  {{ parseResult.valid ? '有效' : '无效' }}
                </el-tag>
              </el-descriptions-item>
              <template v-if="parseResult.result">
                <el-descriptions-item v-for="(value, key) in parseResult.result" :key="key" :label="String(key)">
                  {{ typeof value === 'object' ? JSON.stringify(value) : value }}
                </el-descriptions-item>
              </template>
              <el-descriptions-item v-if="parseResult.error" label="错误">
                {{ parseResult.error }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
        
        <el-card style="margin-top: 20px;">
          <template #header>
            <span>LLM测试用例生成</span>
          </template>
          <el-form :inline="true">
            <el-form-item label="协议">
              <el-select v-model="testProtocol" style="width: 150px;">
                <el-option label="Modbus TCP" value="modbus_tcp" />
                <el-option label="IEC 61850" value="iec61850" />
                <el-option label="DNP3" value="dnp3" />
              </el-select>
            </el-form-item>
            <el-form-item label="用例数量">
              <el-input-number v-model="testCount" :min="1" :max="100" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="generateTests" :loading="generating">生成</el-button>
            </el-form-item>
          </el-form>
          
          <div v-if="generatedTests.length > 0" class="test-results">
            <el-table :data="generatedTests" stripe size="small">
              <el-table-column prop="function_code" label="功能码" width="150" />
              <el-table-column prop="raw_hex" label="十六进制" />
              <el-table-column prop="edge_case" label="边界用例" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.edge_case" size="small">是</el-tag>
                  <span v-else>否</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/client'

const protocols = ref<any[]>([])
const selectedProtocol = ref('modbus_tcp')
const packetData = ref('00000000000601030000000A')
const parseResult = ref<any>(null)

const testProtocol = ref('modbus_tcp')
const testCount = ref(10)
const generating = ref(false)
const generatedTests = ref<any[]>([])

const loadProtocols = async () => {
  try {
    const data = await api.get('/protocols/')
    protocols.value = data.protocols.map((name: string) => ({
      name,
      default_port: name === 'modbus_tcp' ? 502 : name === 'iec61850' ? 102 : 20000,
    }))
  } catch (error) {
    console.error('Failed to load protocols:', error)
  }
}

const parsePacket = async () => {
  try {
    parseResult.value = await api.post('/protocols/parse', {
      protocol: selectedProtocol.value,
      data: packetData.value,
    })
  } catch (error) {
    ElMessage.error('解析失败')
  }
}

const generateTests = async () => {
  generating.value = true
  try {
    const data = await api.post('/protocols/generate-tests', {
      protocol: testProtocol.value,
      num_testcases: testCount.value,
    })
    generatedTests.value = data.testcases || []
    ElMessage.success('生成完成')
  } catch (error) {
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

onMounted(loadProtocols)
</script>

<style scoped>
.protocols-page {
  padding: 20px;
}

.protocol-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.protocol-port {
  color: #666;
  font-size: 12px;
}

.parse-result {
  margin-top: 20px;
}

.test-results {
  margin-top: 20px;
}
</style>
