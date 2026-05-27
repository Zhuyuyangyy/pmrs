import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('@/pages/ProjectsPage.vue'),
  },
  {
    path: '/projects/new',
    name: 'NewProject',
    component: () => import('@/pages/NewProjectPage.vue'),
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: () => import('@/pages/ProjectDetailPage.vue'),
  },
  {
    path: '/vulnerabilities',
    name: 'Vulnerabilities',
    component: () => import('@/pages/VulnerabilitiesPage.vue'),
  },
  {
    path: '/scans',
    name: 'Scans',
    component: () => import('@/pages/ScansPage.vue'),
  },
  {
    path: '/protocols',
    name: 'Protocols',
    component: () => import('@/pages/ProtocolsPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
