<template>
  <el-config-provider :locale="zhCn">
    <div id="app">
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-icon><Monitor /></el-icon>
            <span class="title">PMRS - 工业控制协议漏洞挖掘系统</span>
          </div>
          <div class="header-right">
            <el-button type="primary" @click=".push('/projects/new')">
              <el-icon><Plus /></el-icon> 新建项目
            </el-button>
          </div>
        </el-header>
        <el-container>
          <el-aside width="200px" class="sidebar">
            <el-menu :default-active=".path" router>
              <el-menu-item index="/">
                <el-icon><DataAnalysis /></el-icon>
                <span>仪表盘</span>
              </el-menu-item>
              <el-menu-item index="/projects">
                <el-icon><Folder /></el-icon>
                <span>项目管理</span>
              </el-menu-item>
              <el-menu-item index="/vulnerabilities">
                <el-icon><Warning /></el-icon>
                <span>漏洞管理</span>
              </el-menu-item>
              <el-menu-item index="/scans">
                <el-icon><Search /></el-icon>
                <span>扫描记录</span>
              </el-menu-item>
              <el-menu-item index="/protocols">
                <el-icon><Connection /></el-icon>
                <span>协议分析</span>
              </el-menu-item>
            </el-menu>
          </el-aside>
          <el-main class="main-content">
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import {
  Monitor, Plus, DataAnalysis, Folder, Warning, Search, Connection
} from '@element-plus/icons-vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.header {
  background: #001529;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
}

.header-right {
  display: flex;
  gap: 10px;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e8e8e8;
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
